"""Human-exception-gated metadata projection recovery; original attempt preserved.

Interprets a finite primitive/symbolic NumPy pickle grammar; never imports NumPy,
uses a pickle loader, constructs encoded class objects, reads models or resumes an assay.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import pickletools
import re
import resource
import signal
import sys
import time

ROOT = Path('/Users/cubres/Documents/Neurogolf')
HERE = ROOT / 'research/codex_casmi_v6_followthrough_20261014T2019Z'
PACKET = HERE / 'metadata_primitive_projection_recovery_source'
WRAPPER = PACKET / 'root_projection_recovery_deadline_once.source.py'
PRESERVED = PACKET / 'PRESERVED_ATTEMPT_BINDINGS.json'
PRESERVED_SHA = '23242b15b8f1c5b92ee4bcf501f443a10be3dde83245c1c183360852ed821fe9'
FULL = ROOT / 'research/codex_campaign_20261003T1439Z/full_fp_private_dataset_20261003T203331305453Z'
CW = Path('/Users/cubres/Documents/Clauding/casmi_work')
INVENTORY = HERE / 'root_metadata_format_forensics_20261015_once/RESULT.json'
INVENTORY_SHA = '790a73b589d188e647998c98af9fe865509f2d0af70dfc921b84354c4ec90ff9'
INPUTS = (
    ('full_structure_metadata',FULL/'fp_meta.pkl',17095875,'88411e98cec6f862f7b121dbc27b807e5e18782416219fe2b11566deb3254132',275810,10395,3),
    ('full_pool_metadata',FULL/'pool_meta.pkl',64843052,'53c276a6625f38c90d93e3a8c23c25a2d08712754358b1160f6683e42a922324',711705,10395,5),
    ('clean_structure_metadata',CW/'up_train/fp_meta.pkl',17095875,'d6ad0dd33bf66e92c5a85054b7f914b4ac538fc4b06c4aabca8d0df9f985b85b',275810,6930,3),
    ('clean_pool_metadata',CW/'pool_meta.pkl',64843052,'069c01f0d42affd7b46c5d5b7c56b7eb20e4ca0a8806a0b2e0772c4b1de049f5',711705,6930,5),
)
LIMITS = dict(per_file_bytes=80*(1<<20),total_bytes=180*(1<<20),opcodes_per_file=8000000,
              stack_entries=4096,memo_entries=2000000,list_items=2000000,
              literal_text_bytes=1<<20,required_key_bytes=1024,
              wall_seconds=240,peak_rss_bytes=768*(1<<20),output_bytes_per_file=64*(1<<20))
ALLOWED_SYMBOLS = {('numpy','dtype'),('numpy','ndarray'),('numpy._core.multiarray','_reconstruct')}
UNICODE_CODE = re.compile(r'U([1-9][0-9]{0,2})\Z')
NUMERIC_CODE = re.compile(r'(?:[iu](?:1|2|4|8)|f(?:2|4|8)|b1)\Z')


class GateError(Exception):
    pass


def need(ok, code):
    if not ok:
        raise GateError(code)


def rss_gate():
    need(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss <= LIMITS['peak_rss_bytes'],'RSS_CAP')


def pinned_body(path,expected,cap=131072):
    need(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'PINNED_PATH')
    with path.open('rb') as stream: body = stream.read(cap+1)
    need(len(body) <= cap and hashlib.sha256(body).hexdigest() == expected,'PINNED_BODY')
    return body


def preserved_attempts():
    lineage = json.loads(pinned_body(PRESERVED,PRESERVED_SHA))
    need(lineage['status'] == 'ORIGINAL_PROJECTION_AND_ASSAY_PERMANENTLY_CONSUMED'
         and lineage['all_prior_markers_remain_consumed'] is True
         and lineage['same_query_assay_authorized'] is False,'PRESERVED_LINEAGE_SCOPE')
    for entry in lineage['artifacts']:
        relative = Path(entry['path'])
        need(not relative.is_absolute() and '..' not in relative.parts,'PRESERVED_RELATIVE_PATH')
        pinned_body(HERE/relative,entry['sha256'])


def write_json(path, value):
    fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    digest, total = hashlib.sha256(),0
    with os.fdopen(fd,'wb') as stream:
        for chunk in json.JSONEncoder(ensure_ascii=False,separators=(',',':'),allow_nan=False).iterencode(value):
            body = chunk.encode('utf-8',errors='strict')
            total += len(body)
            need(total <= LIMITS['output_bytes_per_file'],'OUTPUT_BYTE_CAP')
            stream.write(body); digest.update(body)
        need(total+1 <= LIMITS['output_bytes_per_file'],'OUTPUT_BYTE_CAP')
        stream.write(b'\n'); digest.update(b'\n'); total += 1
        stream.flush(); os.fsync(stream.fileno())
    return dict(bytes=total,sha256=digest.hexdigest())


class Symbol:
    __slots__ = ('pair',)
    def __init__(self,pair): self.pair = pair


class DType:
    __slots__ = ('code','width','order','built','item_bytes')
    def __init__(self,code):
        self.code,self.width,self.order,self.built,self.item_bytes = code,None,None,False,None


class ArrayState:
    __slots__ = ('dtype','count','payload','built')
    def __init__(self):
        self.dtype,self.count,self.payload,self.built = None,None,None,False


def dtype_build(target,state):
    need(not target.built and type(state) is tuple and len(state) == 8,'DTYPE_STATE_ARITY_OR_REPEAT')
    version,order,subarray,names,fields,itemsize,alignment,flags = state
    need(type(version) is int and version == 3 and order in ('|','<','>')
         and subarray is None and names is None and fields is None,'DTYPE_STATE_LAYOUT')
    need(all(type(x) is int for x in (itemsize,alignment,flags)),'DTYPE_STATE_INTEGER')
    match = UNICODE_CODE.fullmatch(target.code)
    if target.code == 'O8':
        need((order,itemsize,alignment,flags) == ('|',-1,-1,63),'OBJECT_DTYPE_STATE')
    elif match:
        width = int(match.group(1))
        need(width <= 256 and order in ('<','>') and (itemsize,alignment,flags) == (4*width,4,8),'UNICODE_DTYPE_STATE')
        target.width = width
    elif NUMERIC_CODE.fullmatch(target.code):
        size = int(target.code[1:])
        need((order == '|' if size == 1 else order in ('<','>'))
             and (itemsize,alignment,flags) == (-1,-1,0),'OPAQUE_NUMERIC_DTYPE_STATE')
        target.item_bytes = size
    else:
        raise GateError('UNSUPPORTED_DTYPE')
    target.order,target.built = order,True


def array_build(target,state,sealed_lists):
    need(not target.built and type(state) is tuple and len(state) == 5,'ARRAY_STATE_ARITY_OR_REPEAT')
    version,shape,dtype,fortran,payload = state
    need(type(version) is int and version == 1 and type(shape) is tuple and len(shape) == 1
         and type(shape[0]) is int and 0 < shape[0] <= 711705,'ARRAY_STATE_SHAPE')
    need(type(dtype) is DType and dtype.built and type(fortran) is bool and fortran is False,'ARRAY_STATE_DTYPE_OR_ORDER')
    count = shape[0]
    if dtype.code == 'O8':
        need(type(payload) is list and len(payload) == count
             and all(type(value) is str for value in payload),'OBJECT_ARRAY_PAYLOAD')
        sealed_lists.add(id(payload))
        payload = tuple(payload)  # NumPy BUILD copies an object-list payload.
    elif dtype.width is not None:
        need(type(payload) is bytes and len(payload) == count*dtype.width*4,'UNICODE_ARRAY_PAYLOAD')
    elif dtype.item_bytes is not None:
        need(type(payload) is bytes and len(payload) == count*dtype.item_bytes,'OPAQUE_NUMERIC_ARRAY_PAYLOAD')
        payload = None  # Never interpret or export numeric metadata-array values.
    else:
        raise GateError('UNSUPPORTED_ARRAY_DTYPE')
    target.dtype,target.count,target.payload,target.built = dtype,count,payload,True


def parse_primitive_metadata(raw):
    reader = io.BytesIO(raw)
    stack,memo,sealed_lists = [],[],set()
    marker = object()
    frame_end,started,root_dict = None,False,None

    def push(value):
        stack.append(value); need(len(stack) <= LIMITS['stack_entries'],'STACK_CAP')
    def pop():
        need(bool(stack),'STACK_UNDERFLOW'); return stack.pop()
    def marked():
        values = []
        while stack and stack[-1] is not marker: values.append(pop())
        need(bool(stack),'MISSING_MARK'); pop(); values.reverse(); return values
    def extend_strings(target,values):
        need(type(target) is list and id(target) not in sealed_lists
             and all(type(value) is str for value in values),'LIST_STRING_SCHEMA_OR_SEALED')
        need(len(target)+len(values) <= LIMITS['list_items'],'LIST_ITEM_CAP')
        target.extend(values)
    def assign(target,values):
        need(target is root_dict and len(values)%2 == 0,'ROOT_DICTIONARY_SCHEMA')
        for key,value in zip(values[::2],values[1::2]):
            need(type(key) is str and len(key.encode('utf-8')) <= 128 and key not in target,'ROOT_KEY_SCHEMA_OR_DUPLICATE')
            need(type(value) in (int,list,ArrayState),'ROOT_VALUE_SCHEMA')
            if type(value) is ArrayState: need(value.built,'UNBUILT_ROOT_ARRAY')
            target[key] = value
        need(len(target) <= 5,'ROOT_FIELD_CAP')

    for index,(operation,argument,position) in enumerate(pickletools.genops(reader),1):
        need(index <= LIMITS['opcodes_per_file'],'OPCODE_CAP')
        if index%10000 == 0: rss_gate()
        name,end = operation.name,reader.tell()
        if frame_end is not None:
            need(position <= frame_end,'FRAME_POSITION')
            if position == frame_end: frame_end = None
            else: need(end <= frame_end and name != 'FRAME','FRAME_OPERAND_BOUNDARY')
        if name == 'PROTO':
            need(not started and index == 1 and argument == 4,'PROTOCOL_SCHEMA'); started = True
        elif name == 'FRAME':
            need(started and type(argument) is int and 0 <= argument <= len(raw)-end,'FRAME_LENGTH')
            frame_end = end+argument
        elif name == 'STOP':
            need(started and end == len(raw) and (frame_end is None or end == frame_end)
                 and len(stack) == 1 and stack[0] is root_dict,'STOP_SCHEMA')
            return root_dict
        elif name == 'MARK': push(marker)
        elif name in ('BININT','BININT1','BININT2'):
            need(type(argument) is int and -(1<<31) <= argument < (1<<31),'INTEGER_CAP'); push(argument)
        elif name in ('SHORT_BINUNICODE','BINUNICODE'):
            need(type(argument) is str and len(argument.encode('utf-8')) <= LIMITS['literal_text_bytes'],'TEXT_CAP'); push(argument)
        elif name in ('SHORT_BINBYTES','BINBYTES'):
            need(type(argument) is bytes and len(argument) <= LIMITS['per_file_bytes'],'BYTES_CAP'); push(argument)
        elif name == 'NONE': push(None)
        elif name in ('NEWTRUE','NEWFALSE'): push(name == 'NEWTRUE')
        elif name == 'EMPTY_DICT':
            need(root_dict is None and not stack,'NESTED_DICTIONARY_UNSUPPORTED'); root_dict = {}; push(root_dict)
        elif name == 'EMPTY_LIST': push([])
        elif name == 'APPENDS':
            values = marked(); need(bool(stack),'LIST_STACK'); extend_strings(stack[-1],values)
        elif name == 'SETITEMS':
            values = marked(); need(bool(stack),'DICT_STACK'); assign(stack[-1],values)
        elif name == 'TUPLE': push(tuple(marked()))
        elif name in ('TUPLE1','TUPLE3'):
            count = int(name[-1]); values = [pop() for _ in range(count)]; values.reverse(); push(tuple(values))
        elif name == 'MEMOIZE':
            need(bool(stack) and len(memo) < LIMITS['memo_entries'],'MEMO_CAP'); memo.append(stack[-1])
        elif name == 'BINGET':
            need(type(argument) is int and 0 <= argument < len(memo),'MEMO_REFERENCE'); push(memo[argument])
        elif name == 'STACK_GLOBAL':
            class_name,module = pop(),pop()
            need(type(module) is str and type(class_name) is str and (module,class_name) in ALLOWED_SYMBOLS,'GLOBAL_SYMBOL')
            push(Symbol((module,class_name)))
        elif name == 'REDUCE':
            arguments,target = pop(),pop()
            need(type(target) is Symbol and type(arguments) is tuple,'REDUCE_TARGET_OR_ARGS')
            if target.pair == ('numpy','dtype'):
                need(len(arguments) == 3 and type(arguments[0]) is str and len(arguments[0]) <= 8
                     and arguments[1] is False and arguments[2] is True,'DTYPE_CONSTRUCTOR_ARGS')
                need(arguments[0] == 'O8' or UNICODE_CODE.fullmatch(arguments[0]) or NUMERIC_CODE.fullmatch(arguments[0]),'UNSUPPORTED_DTYPE_CODE')
                push(DType(arguments[0]))
            elif target.pair == ('numpy._core.multiarray','_reconstruct'):
                need(len(arguments) == 3 and type(arguments[0]) is Symbol
                     and arguments[0].pair == ('numpy','ndarray') and type(arguments[1]) is tuple
                     and len(arguments[1]) == 1 and type(arguments[1][0]) is int and arguments[1][0] == 0
                     and type(arguments[2]) is bytes and arguments[2] == b'b','ARRAY_SHELL_ARGS')
                push(ArrayState())
            else: raise GateError('UNSUPPORTED_CONSTRUCTOR_SYMBOL')
        elif name == 'BUILD':
            state = pop(); need(bool(stack),'BUILD_STACK'); target = stack[-1]
            if type(target) is DType: dtype_build(target,state)
            elif type(target) is ArrayState: array_build(target,state,sealed_lists)
            else: raise GateError('UNSUPPORTED_BUILD_TARGET')
        else:
            raise GateError('UNSUPPORTED_OPCODE')
    raise GateError('MISSING_STOP')


def required_projection(root,count,nbits,fields):
    need(type(root) is dict and len(root) == fields and 'keys' in root and 'nbits' in root,'REQUIRED_FIELDS')
    need(type(root['nbits']) is int and root['nbits'] == nbits,'REQUIRED_NBITS')
    source = root['keys']
    if type(source) is list:
        need(len(source) == count,'REQUIRED_KEYS_COUNT'); keys = tuple(source); encoding = 'builtin string list'
    elif type(source) is ArrayState:
        need(source.built and source.count == count,'REQUIRED_ARRAY_COUNT')
        if source.dtype.code == 'O8':
            keys = source.payload; encoding = 'symbolic object ndarray with builtin-string payload'
        elif source.dtype.width is not None:
            width,raw = source.dtype.width,source.payload
            codec = 'utf-32-le' if source.dtype.order == '<' else 'utf-32-be'
            values = []
            for offset in range(0,len(raw),4*width):
                value = raw[offset:offset+4*width].decode(codec,errors='strict')
                value = value.rstrip('\x00')
                need('\x00' not in value,'UNICODE_INTERIOR_NUL')
                values.append(value)
            keys = tuple(values); encoding = 'symbolic explicit-endian fixed Unicode ndarray'
        else: raise GateError('REQUIRED_KEYS_NONSTRING_DTYPE')
    else: raise GateError('REQUIRED_KEYS_TYPE')
    digest = hashlib.sha256()
    for value in keys:
        need(type(value) is str and value != '' and '\x00' not in value,'REQUIRED_KEY_STRING')
        body = value.encode('utf-8',errors='strict')
        need(len(body) <= LIMITS['required_key_bytes'],'REQUIRED_KEY_BYTE_CAP')
        digest.update(len(body).to_bytes(4,'big')); digest.update(body)
    return dict(keys=keys,nbits=nbits),dict(count=count,nbits=nbits,source_encoding=encoding,
        ordered_key_sha256=digest.hexdigest(),order_hash_encoding='4-byte big-endian UTF8 length then exact UTF8 bytes',
        normalization=False,sorting=False,deduplication=False,encoded_global_calls=False)


def alarm(signum,frame):
    raise GateError('PROJECTION_DEADLINE')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--wrapper-sha256',required=True)
    parser.add_argument('--human-exception-sha256',required=True)
    args = parser.parse_args()
    need(sys.platform == 'darwin' and sys.flags.isolated == 1 and sys.dont_write_bytecode
         and Path(__file__).absolute() == PACKET/'project_required_metadata_recovery_once.source.py','ROOT_RUNTIME_SCHEMA')
    with Path(__file__).open('rb') as stream: source_body = stream.read(65537)
    need(len(source_body) <= 65536 and hashlib.sha256(source_body).hexdigest() == args.source_sha256,'SOURCE_PIN')
    pinned_body(WRAPPER,args.wrapper_sha256)
    need(INVENTORY.is_file() and not any(p.is_symlink() for p in (INVENTORY,*INVENTORY.parents)),'INVENTORY_PATH')
    with INVENTORY.open('rb') as stream: inventory_body = stream.read(65537)
    need(len(inventory_body) <= 65536 and hashlib.sha256(inventory_body).hexdigest() == INVENTORY_SHA,'INVENTORY_PIN')
    prior = json.loads(inventory_body)
    need(prior['status'] == 'COMPLETED_INERT_METADATA_FORMAT_INVENTORY_ONLY'
         and prior['pickle_object_deserialization'] is False and prior['global_calls_executed'] is False,'INVENTORY_STATUS')
    # This distinct recovery cannot consume a new attempt without a direct human exception.
    waiver_path = PACKET / 'PRIVATE_HUMAN_RECOVERY_AUTHORIZATION.json'
    need(waiver_path.is_file() and not any(p.is_symlink() for p in (waiver_path,*waiver_path.parents)),'HUMAN_EXCEPTION_PATH')
    with waiver_path.open('rb') as stream: waiver_body = stream.read(65537)
    need(len(waiver_body) <= 65536 and hashlib.sha256(waiver_body).hexdigest() == args.human_exception_sha256,'HUMAN_EXCEPTION_PIN')
    waiver = json.loads(waiver_body)
    need(waiver['status'] == 'HUMAN_AUTHORIZED_ONE_PROJECTION_RECOVERY'
         and waiver['authorization_origin'] == 'direct_human_user_message'
         and type(waiver['message_reference']) is str and 0 < len(waiver['message_reference']) <= 512
         and waiver['recovery_source_sha256'] == args.source_sha256
         and waiver['recovery_wrapper_sha256'] == args.wrapper_sha256
         and waiver['preserved_attempt_bindings_sha256'] == PRESERVED_SHA
         and waiver['recovery_scope'] == 'one_private_required_metadata_projection_only'
         and type(waiver['maximum_recovery_dispatches']) is int and waiver['maximum_recovery_dispatches'] == 1
         and waiver['root_only_dispatch'] is True and waiver['retry_authorized'] is False
         and waiver['same_query_assay_authorized'] is False
         and waiver['preserve_all_old_sources_markers_partials'] is True
         and waiver['previous_projection_attempt_remains_consumed'] is True
         and waiver['old_assay_attempt_remains_consumed'] is True,'HUMAN_EXCEPTION_SCOPE')
    preserved_attempts()
    marker = HERE / 'METADATA_PRIMITIVE_PROJECTION_RECOVERY_ONE_ATTEMPT.json'
    out = HERE / 'root_metadata_primitive_projection_recovery_20261015_once'
    need(not marker.exists() and not out.exists(),'PROJECTION_PURPOSE_CONSUMED')
    write_json(marker,dict(purpose='human-authorized private primitive metadata projection recovery',consumed_before_input_read=True,
        source_sha256=args.source_sha256,wrapper_sha256=args.wrapper_sha256,
        inventory_sha256=INVENTORY_SHA,preserved_attempt_bindings_sha256=PRESERVED_SHA,
        human_exception_sha256=args.human_exception_sha256,retry_authorized=False,
        paired_assay_authorized=False))
    out.mkdir(mode=0o700,exist_ok=False)
    started,current_input = time.monotonic(),None
    signal.signal(signal.SIGALRM,alarm); signal.setitimer(signal.ITIMER_REAL,LIMITS['wall_seconds'])
    try:
        records,references,total = [],{},0
        for label,path,size,expected,count,nbits,fields in INPUTS:
            current_input = label
            need(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)),'INPUT_PATH')
            need(path.stat().st_size == size <= LIMITS['per_file_bytes'],'INPUT_BYTE_CAP')
            total += size; need(total <= LIMITS['total_bytes'],'TOTAL_BYTE_CAP')
            with path.open('rb') as stream: raw = stream.read(size+1)
            need(len(raw) == size and hashlib.sha256(raw).hexdigest() == expected,'INPUT_PIN'); rss_gate()
            parsed = parse_primitive_metadata(raw); rss_gate()
            projection,binding = required_projection(parsed,count,nbits,fields); rss_gate()
            role = 'structure' if 'structure' in label else 'pool'
            if label.startswith('full_'): references[role] = projection['keys']
            else: need(projection['keys'] == references[role],'FULL_CLEAN_EXACT_KEY_ORDER')
            output = label+'.json'
            stored = write_json(out/output,projection)
            records.append(dict(input_label=label,original_bytes=size,original_sha256=expected,
                output_file=output,output_bytes=stored['bytes'],output_sha256=stored['sha256'],**binding))
            del raw,parsed,projection
            rss_gate()
        # Original identity files remain intact; detect local drift without any array/model load.
        for _,path,size,expected,_,_,_ in INPUTS:
            with path.open('rb') as stream: body = stream.read(size+1)
            need(len(body) == size and hashlib.sha256(body).hexdigest() == expected,'ORIGINAL_INPUT_CHANGED')
            del body
        preserved_attempts()
        rss_gate()
        write_json(out/'DERIVED_METADATA_MANIFEST.json',dict(status='COMPLETE_PRIVATE_PRIMITIVE_METADATA_PROJECTION_RECOVERY_ONLY',
            inputs=records,source_sha256=args.source_sha256,wrapper_sha256=args.wrapper_sha256,
            inventory_sha256=INVENTORY_SHA,preserved_attempt_bindings_sha256=PRESERVED_SHA,limits=LIMITS,
            human_exception_sha256=args.human_exception_sha256,original_failure_sha256='2b75fc159bf50964e8afc01d6c50b8ae99bd50fb88f605d830e82a7495457290',
            full_clean_structure_order_exact=True,full_clean_pool_order_exact=True,
            preserved_attempts_unchanged=True,all_old_markers_permanently_consumed=True,
            original_inputs_unchanged=True,primitive_data_decoded=True,pickle_loader_used=False,
            encoded_class_objects_constructed=False,numpy_imported=False,encoded_globals_invoked=False,
            models_or_numeric_arrays_loaded=False,held_roles_evaluated=False,network_calls=0,
            private_only=True,paired_assay_authorized=False,human_exception_required_for_same_query_assay=True,
            official_score=None,seconds=time.monotonic()-started,
            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        print('COMPLETE_PRIVATE_PRIMITIVE_METADATA_PROJECTION_RECOVERY_ONLY',flush=True); return 0
    except BaseException as error:
        gate = str(error) if type(error) is GateError else 'PARSER_CODEC_OR_IO_FAILURE'
        try:
            write_json(out/'FAILURE.json',dict(status='HOLD_CONSUMED_PRIMITIVE_METADATA_PROJECTION_RECOVERY',
                error_type=type(error).__name__,gate=gate,input_label=current_input,seconds=time.monotonic()-started,
                retry_authorized=False,paired_assay_authorized=False,official_score=None))
        except BaseException: print('PRIVATE_PROJECTION_FAILURE_RECORD_UNWRITABLE',flush=True)
        print('HOLD_CONSUMED_PRIMITIVE_METADATA_PROJECTION_RECOVERY',flush=True); return 2
    finally: signal.setitimer(signal.ITIMER_REAL,0)


if __name__ == '__main__':
    raise SystemExit(main())

