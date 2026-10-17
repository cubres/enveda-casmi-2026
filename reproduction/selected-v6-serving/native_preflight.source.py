"""One consumed job: bounded path/version observations, then same-PID driver exec.

Package strings record drift; they do not qualify compatibility or attest the
container image. Root must separately bind image, artifacts, rights and privacy.
This source never runs a model, repairs an environment or selects scientific rows.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import stat
import sys
import time

WORK = Path('/kaggle/working/casmi_v6_native_once')
SCIENCE = {
    'native_canary_and_infer.source.py':'612700a8a5caa8b3711a332a8894cbbf162821eca53b3e79d839e5aa29aca487',
    'v6_single_view_scoring.source.py':'7b5c7d8125b9f930927b2675926dfe4f444bea5cd5625338c03ef165e30ca6d3',
    'project_required_metadata_recovery_once.source.py':'1f10d75ba7daa86e6979811ffb382f28c34bb04436c2291dd69eff2bb8f42294',
    'fpmodel.py':'69f2656778a08233e22235bf4853f0b3d2420b431390a32d6c8ed453cde85c76',
}
SOURCE_NAMES = frozenset((*SCIENCE, 'native_preflight.source.py', 'preflight_launcher.source.py'))
INPUT_SHA = {
    'checkpoint':'9c46ca4fcf19002fecbcded0d0808e8a81e3a25a143e684e259f265c44a5be31',
    'full_mask':'f771cb6aa87a418b06d9abfbdac0c1759040afb955b9dfa59e8932105a65bdc6',
    'spectrum_cache':'99dbf966d2607e2da8085a6550206a71fc912d2c90b9555a725a2569e4af4500',
    'structure_roles':'fe654a3f5f655df3897a344ca222e01a9f555a7dfd22a786e6cb32b126c76049',
    'pool_meta':'53c276a6625f38c90d93e3a8c23c25a2d08712754358b1160f6683e42a922324',
    'pool_mass':'0d28d5c288201e3598ba2fffea7f3d7284e397341ab0d72e5111b4cc67dabd1e',
    'pool_fp':'84afb2d17d567359963f1941c4c8b20523770aad4167ccc0bd715530360611e0',
    'structure_meta':'88411e98cec6f862f7b121dbc27b807e5e18782416219fe2b11566deb3254132',
    'rdkit_wheel':'c69a40ad52a2489cf592d55b41f5f6fa482f028341c038f3ed7d6b46834d1d3d',
    'train':'9423f90ec08b941a9646b535bf0606183e86ff0c5a297978f5a70693d41bcd98',
}
FIXED = {
    'schema':'casmi-v6-native-one-job/2',
    'root_authorized_one_job':True, 'conditional_full_inference_after_canary':True,
    'public_source_safe':True, 'explicit_canary_identifiers_embedded':False,
    'private_input_public_notebook_compatibility_qualified':True,
    'competition_use_and_mount_rights_qualified':True,
    'dependency_image_or_offline_bootstrap_qualified':True,
    'external_linux_rss_supervisor_qualified':True,
    'full_bank_row_alignment_source_reviewed':True,
    'full_bank_preparation_manifest_sha256':'5b08ca4b830de1558be4ce568a10f0997b5fa2fe875a872dcd6a216f901fd9ef',
    'mode':'PURE_FULL10395_SINGLE_VIEW',
    'spectrum_policy':'first_usable_in_original_test_row_order',
    'candidate_policy':'observed_neutral_mass_median_10ppm_then_empty_30ppm',
    'fallback_policy':'valid_window_candidates_by_mass_distance_or_hold_if_none',
    'candidate_canary_policy':'first_optimizer_structure_in_full_bank_order',
    'canary_spectrum_policy':'minimum_original_source_row_nonempty_optimizer_cache',
    'tie_policy':'stable_original_full_bank_order',
    'candidate_bank_policy':'exact_existing_full711705_bank_no_rebuild',
    'ranker_blend_training_or_official_submission_authorized':False,
    'retry_authorized':False, 'device':'cuda:0',
    'wall_seconds':1800, 'canary_wall_seconds':300, 'peak_rss_limit_bytes':20*(1 << 30),
}
MOUNTS = {
    'full_bank':{'kind':'dataset','ref':'prvsiyan/casmi26-full-fingerprint-inputs','version':1},
    'spectra':{'kind':'dataset','ref':'prvsiyan/casmi26-spec-fp','version':1},
    'rdkit':{'kind':'dataset','ref':'prvsiyan/rdkit-wheel-offline','version':1},
    'trainer':{'kind':'kernel','ref':'prvsiyan/casmi-fp-trainer-merged-spectra','version':6,'native_id':358388543},
    'competition':{'kind':'competition','ref':'enveda-CASMI26-molecule-id-mass-spectra'},
}
ROUTES = {
    'checkpoint':{'mount':'trainer','relative_path':'casmi_structure_uniform_20261014/training/full_spectrum/best_full_model.pt'},
    'full_mask':{'mount':'full_bank','relative_path':'fp_bits.npy'},
    'pool_fp':{'mount':'full_bank','relative_path':'pool_fp.npy'},
    'pool_mass':{'mount':'full_bank','relative_path':'pool_mass.npy'},
    'pool_meta':{'mount':'full_bank','relative_path':'pool_meta.pkl'},
    'structure_meta':{'mount':'full_bank','relative_path':'fp_meta.pkl'},
    'structure_roles':{'mount':'full_bank','relative_path':'roles_by_structure.b64'},
    'spectrum_cache':{'mount':'spectra','relative_path':'spec.npz'},
    'rdkit_wheel':{'mount':'rdkit','relative_path':'rdkit-2026.3.3-cp312-cp312-manylinux_2_28_x86_64.whl'},
    'train':{'mount':'competition','relative_path':'train.parquet'},
}
RUNTIME_KEYS = frozenset(('python','numpy','torch','pandas','pyarrow','pillow'))
PUBLIC_FAILURE_CODES = frozenset((
    'MOUNT_FILE_SIZE_DRIFT','MISSING_OR_AMBIGUOUS_APPROVED_MOUNT','SYMLINK_PATH_REJECTED',
    'REGULAR_EXPECTED_PATH_TYPE','ANCESTOR_DIRECTORY_REQUIRED','DISTINCT_TEN_ARTIFACT_PATHS',
    'EXACT_NATIVE_ABI','NATIVE_GLIBC_ABI','ACTUAL_CUDA_T4_REQUIRED',
    'RDKIT_BOOTSTRAP_REMAINS_DRIVER_OWNED','ABSOLUTE_PACKAGE_ORIGINS',
    'PREFLIGHT_EXHAUSTED_CANARY_OR_TOTAL_BUDGET','GLOBAL_CANARY_DEADLINE',
    'GLOBAL_CANARY_DEADLINE_BEFORE_EXEC','SOURCE_OR_POLICY_BYTE_DRIFT','FINAL_CONFIG_CAP',
))


def need(ok, code):
    if not ok:
        raise ValueError(code)


def scientific_source_pins():
    return dict(SCIENCE)


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')


def parse(raw):
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'DUPLICATE_JSON_KEY')
            result[key]=value
        return result
    def reject(value):
        raise ValueError('NONFINITE_JSON_CONSTANT')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)


def root_options(binding):
    if binding['kind']=='competition':
        return ('/kaggle/input/'+binding['ref'],'/kaggle/input/competitions/'+binding['ref'])
    owner,slug=binding['ref'].split('/')
    family='datasets' if binding['kind']=='dataset' else 'notebooks'
    return ('/kaggle/input/'+slug,'/kaggle/input/'+family+'/'+owner+'/'+slug)


def validate_policy(policy):
    keys={'schema','fixed_config','mounts','file_routes','source_files','immutable_platform_image',
          'immutable_image_metadata_qualified','dependency_route_source_reviewed',
          'native_compatibility_before_canary','runtime_observation_is_not_compatibility_approval'}
    need(type(policy)is dict and set(policy)==keys and policy['schema']=='casmi-v6-preflight-policy/1','POLICY_SCHEMA')
    need(policy['immutable_image_metadata_qualified'] is True
         and policy['dependency_route_source_reviewed'] is True
         and policy['native_compatibility_before_canary']=='UNKNOWN'
         and policy['runtime_observation_is_not_compatibility_approval'] is True,'EXTERNAL_IMAGE_AND_ROUTE_ADMISSION')
    need(type(policy['immutable_platform_image'])is str and re.fullmatch(
        r'gcr\.io/kaggle-private-byod/python@sha256:[0-9a-f]{64}',policy['immutable_platform_image']), 'IMMUTABLE_PLATFORM_IMAGE_BINDING')
    cfg=policy['fixed_config']
    need(type(cfg)is dict and set(cfg)==set(FIXED)|{'files','source_files'},'FIXED_CONFIG_SCHEMA')
    need(all(type(cfg[k])is type(v) and cfg[k]==v for k,v in FIXED.items()),'EXACT_FIXED_SCIENCE_RIGHTS_AND_BUDGET')
    need(cfg['source_files']==SCIENCE and set(policy['source_files'])==SOURCE_NAMES
         and all(type(v)is str and re.fullmatch('[0-9a-f]{64}',v) for v in policy['source_files'].values())
         and all(policy['source_files'][k]==v for k,v in SCIENCE.items()),'FROZEN_SOURCE_MAP')
    need(type(cfg['files'])is dict and set(cfg['files'])==set(INPUT_SHA),'EXACT_TEN_INPUTS')
    for label,record in cfg['files'].items():
        need(type(record)is dict and set(record)=={'bytes','sha256'} and type(record['bytes'])is int
             and 0<record['bytes']<=8*(1 << 30) and record['sha256']==INPUT_SHA[label], 'FIXED_INPUT_BYTE_BINDING')
    need(type(policy['mounts'])is dict and set(policy['mounts'])==set(MOUNTS),'EXACT_APPROVED_MOUNTS')
    for label,binding in MOUNTS.items():
        record=policy['mounts'][label]
        need(type(record)is dict and set(record)==set(binding)|{'allowed_roots'}
             and all(type(record[k])is type(v) and record[k]==v for k,v in binding.items())
             and record['allowed_roots']==list(root_options(binding)), 'IMMUTABLE_MOUNT_IDENTITY_AND_BOUNDED_LAYOUTS')
    need(policy['file_routes']==ROUTES,'EXACT_RELATIVE_FILE_ROUTES')
    return policy


def checked_path(path, directory=False):
    path=Path(path)
    need(path.is_absolute() and '..' not in path.parts,'ABSOLUTE_NONEScaping_PATH')
    for item in (path,*path.parents):
        try:
            mode=item.lstat().st_mode
        except FileNotFoundError:
            return False
        need(not stat.S_ISLNK(mode),'SYMLINK_PATH_REJECTED')
        if item!=path:
            need(stat.S_ISDIR(mode),'ANCESTOR_DIRECTORY_REQUIRED')
    need(stat.S_ISDIR(mode) if path==Path('/') else True,'ROOT_DIRECTORY_REQUIRED')
    mode=path.lstat().st_mode
    need(stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode),'REGULAR_EXPECTED_PATH_TYPE')
    return True


def resolve_unique_root(allowed_roots, relative_sizes):
    """Two explicit roots at most; no glob, recursive discovery or private listing."""
    need(type(allowed_roots)is list and 1<=len(allowed_roots)<=2
         and len(set(allowed_roots))==len(allowed_roots),'BOUNDED_UNIQUE_ROOT_OPTIONS')
    need(type(relative_sizes)is dict and 1<=len(relative_sizes)<=12,'BOUNDED_SENTINEL_SET')
    for relative,size in relative_sizes.items():
        part=Path(relative)
        need(type(relative)is str and relative and not part.is_absolute() and '..' not in part.parts
             and str(part)==relative and '\\' not in relative and '\x00' not in relative
             and (size is None or type(size)is int and size>0),'EXACT_SAFE_RELATIVE_SENTINEL')
    matches=[]
    for root_text in allowed_roots:
        root=Path(root_text)
        need(str(root)==root_text,'CANONICAL_ROOT_PATH')
        if not checked_path(root,directory=True):
            continue
        complete=True
        for relative,size in relative_sizes.items():
            item=root/relative
            if not checked_path(item):
                complete=False
                continue
            observed=item.stat().st_size
            need(observed>0 and (size is None or observed==size),'MOUNT_FILE_SIZE_DRIFT')
        if complete:
            matches.append(root)
    need(len(matches)==1,'MISSING_OR_AMBIGUOUS_APPROVED_MOUNT')
    return matches[0]


def resolve_mounts(policy):
    roots={}
    for mount,binding in policy['mounts'].items():
        sentinels={route['relative_path']:policy['fixed_config']['files'][label]['bytes']
                   for label,route in policy['file_routes'].items() if route['mount']==mount}
        if mount=='competition':
            sentinels.update({'test.parquet':None,'sample_submission.csv':None})
        roots[mount]=resolve_unique_root(binding['allowed_roots'],sentinels)
    paths={label:str(roots[route['mount']]/route['relative_path']) for label,route in policy['file_routes'].items()}
    need(len(set(paths.values()))==len(paths),'DISTINCT_TEN_ARTIFACT_PATHS')
    return paths,str(roots['competition'])


def remaining_budgets(started,now):
    need(type(started)in(int,float) and type(now)in(int,float) and math.isfinite(started)
         and math.isfinite(now) and 0<=started<=now,'MONOTONIC_CLOCK_BINDING')
    remaining={key:math.floor(seconds-(now-started)) for key,seconds in
               (('canary_wall_seconds',300),('wall_seconds',1800))}
    need(60<=remaining['canary_wall_seconds']<=300 and 60<=remaining['wall_seconds']<=1800,'PREFLIGHT_EXHAUSTED_CANARY_OR_TOTAL_BUDGET')
    return remaining


def finalize_config(policy,paths,competition,runtime,started,now):
    validate_policy(policy)
    need(type(paths)is dict and set(paths)==set(INPUT_SHA),'EXACT_RESOLVED_PATH_SET')
    need(type(runtime)is dict and set(runtime)==RUNTIME_KEYS
         and all(type(v)is str and v and len(v)<=512 and '\n' not in v for v in runtime.values()),'SIX_OBSERVED_RUNTIME_STRINGS')
    cfg=copy.deepcopy(policy['fixed_config'])
    for label,path in paths.items():
        route=policy['file_routes'][label]
        need(path in [str(Path(root)/route['relative_path']) for root in policy['mounts'][route['mount']]['allowed_roots']], 'RESOLVED_PATH_NOT_APPROVED')
        cfg['files'][label]['path']=path
    need(competition in policy['mounts']['competition']['allowed_roots']
         and cfg['files']['train']['path']==str(Path(competition)/'train.parquet'),'COMPETITION_ROOT_AND_TRAIN_MATCH')
    cfg.update(runtime=dict(runtime),competition_root=competition,**remaining_budgets(started,now))
    restored=copy.deepcopy(cfg)
    restored.pop('runtime');restored.pop('competition_root')
    for record in restored['files'].values():record.pop('path')
    restored.update(wall_seconds=1800,canary_wall_seconds=300)
    need(canonical(restored)==canonical(policy['fixed_config']),'ONLY_OBSERVATION_AND_REMAINING_BUDGET_DELTA')
    return cfg


def observe_runtime():
    need(sys.platform=='linux' and sys.version_info[:2]==(3,12) and platform.machine()=='x86_64'
         and sys.byteorder=='little','EXACT_NATIVE_ABI')
    name,version=platform.libc_ver()
    need(name=='glibc' and re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+)*',version)
         and tuple(map(int,version.split('.')[:2]))>=(2,28),'NATIVE_GLIBC_ABI')
    import numpy
    import torch
    import pandas
    import pyarrow
    import PIL
    need('rdkit' not in sys.modules,'RDKIT_BOOTSTRAP_REMAINS_DRIVER_OWNED')
    need(torch.cuda.is_available() and 'T4' in torch.cuda.get_device_name(0),'ACTUAL_CUDA_T4_REQUIRED')
    packages={'numpy':numpy,'torch':torch,'pandas':pandas,'pyarrow':pyarrow,'pillow':PIL}
    runtime={'python':sys.version.split()[0],**{name:str(module.__version__) for name,module in packages.items()}}
    origins={'python':sys.executable,**{name:str(module.__file__) for name,module in packages.items()}}
    need(all(Path(value).is_absolute() and len(value)<=2048 for value in origins.values()),'ABSOLUTE_PACKAGE_ORIGINS')
    return runtime,origins,{'platform':'linux','machine':'x86_64','python_major_minor':[3,12],
        'libc_name':name,'libc_version':version,'device0':torch.cuda.get_device_name(0)}


def bounded_source(path,expected,cap):
    need(checked_path(path) and path.stat().st_size<=cap,'BOUNDED_SOURCE_FILE')
    with path.open('rb') as stream:raw=stream.read(cap+1)
    need(len(raw)<=cap and hashlib.sha256(raw).hexdigest()==expected,'SOURCE_OR_POLICY_BYTE_DRIFT')
    return raw


def write_new(name,raw):
    need(Path(name).name==name,'OUTPUT_BASENAME')
    fd=os.open(WORK/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-sha256',required=True)
    ap.add_argument('--policy-sha256',required=True)
    ap.add_argument('--started-monotonic',type=float,required=True)
    args=ap.parse_args()
    phase='entry'
    try:
        need(sys.flags.isolated==1 and sys.dont_write_bytecode and Path(__file__).absolute()==WORK/'native_preflight.source.py','EXACT_ISOLATED_PREFLIGHT_ROUTE')
        bounded_source(Path(__file__),args.source_sha256,65536)
        policy=parse(bounded_source(WORK/'PREFLIGHT_POLICY.json',args.policy_sha256,65536))
        validate_policy(policy)
        need(policy['source_files']['native_preflight.source.py']==args.source_sha256,'PREFLIGHT_SELF_BINDING')
        remaining_budgets(args.started_monotonic,time.monotonic())
        def expired(signum,frame):raise ValueError('GLOBAL_CANARY_DEADLINE')
        signal.signal(signal.SIGALRM,expired)
        signal.setitimer(signal.ITIMER_REAL,max(0.001,args.started_monotonic+300-time.monotonic()))
        for filename,expected in policy['source_files'].items():
            bounded_source(WORK/filename,expected,2 << 20)
        phase='mount_resolution'
        paths,competition=resolve_mounts(policy)
        phase='runtime_observation'
        runtime,origins,abi=observe_runtime()
        phase='config_freeze'
        config=finalize_config(policy,paths,competition,runtime,args.started_monotonic,time.monotonic())
        raw=canonical(config)
        need(len(raw)<=65536,'FINAL_CONFIG_CAP')
        digest=hashlib.sha256(raw).hexdigest()
        write_new('NATIVE_CONFIG.json',raw)
        write_new('PREFLIGHT_RESULT.json',canonical({'status':'PASS_PREFLIGHT_OBSERVATIONS_ONLY',
            'policy_sha256':args.policy_sha256,'source_sha256':policy['source_files'],'resolved_config_sha256':digest,
            'runtime':runtime,'package_origins':origins,'abi':abi,
            'declared_platform_image':policy['immutable_platform_image'],'image_attested_by_preflight':False,
            'native_compatibility_before_driver_canary':'UNKNOWN','global_start_monotonic':args.started_monotonic,
            'preflight_elapsed_seconds':time.monotonic()-args.started_monotonic,
            'driver_remaining_canary_seconds':config['canary_wall_seconds'],'driver_remaining_total_seconds':config['wall_seconds'],
            'same_pid_exec':True,'private_rows_or_arrays_published':False,'retry_authorized':False}))
        phase='same_pid_exec'
        need(time.monotonic()<args.started_monotonic+300,'GLOBAL_CANARY_DEADLINE_BEFORE_EXEC')
        # ITIMER_REAL survives exec; the outer supervisor independently enforces
        # the absolute300s/1800s deadlines even after driver's own timer setup.
        os.execve(sys.executable,[sys.executable,'-I','-B',str(WORK/'native_canary_and_infer.source.py'),
            '--source-sha256',SCIENCE['native_canary_and_infer.source.py'],
            '--config',str(WORK/'NATIVE_CONFIG.json'),'--config-sha256',digest],dict(os.environ))
        raise ValueError('EXEC_RETURNED')
    except BaseException as error:
        code = str(error) if type(error) is ValueError and str(error) in PUBLIC_FAILURE_CODES else 'PREFLIGHT_FAILED_CLOSED'
        failure = {'status':'HOLD_CONSUMED_PREFLIGHT','phase':phase,
            'error_code':code,'retry_authorized':False,'private_values_published':False}
        write_new('PREFLIGHT_FAILURE.json',canonical(failure))
        print(canonical(failure).decode('utf-8'),flush=True)
        return 2


if __name__=='__main__':
    sys.exit(main())
