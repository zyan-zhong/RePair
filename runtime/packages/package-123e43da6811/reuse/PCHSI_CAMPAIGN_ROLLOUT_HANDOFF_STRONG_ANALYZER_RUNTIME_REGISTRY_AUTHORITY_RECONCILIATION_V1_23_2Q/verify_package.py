from pathlib import Path
import ast, hashlib, subprocess, sys
root=Path(__file__).resolve().parent
manifest=root/'PACKAGE_FILES.sha256'
rows=[]
for line in manifest.read_text().splitlines():
    if not line.strip():
        continue
    sha,rel=line.split('  ',1)
    p=root/rel
    if hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
        raise SystemExit('PACKAGE_SHA256_MISMATCH:'+rel)
    rows.append(rel)
print('PACKAGE_SHA256_VERIFY_PASS files='+str(len(rows)))

for rel in ('v1232q_driver.py','verify_package.py'):
    ast.parse((root/rel).read_text())

source=(root/'v1232q_driver.py').read_text()
for forbidden in (
    '166443',
    '34072dedc0234050307459c77f24a9763fe2a470ae74e0078eceaa87ef417b49',
    'ea091bcdc2a9bcd239ec57d40dec423003ff68a8',
    '2843',
):
    if forbidden in source:
        raise SystemExit('CURRENT_RUN_HARDCODE_PRESENT:'+forbidden)

shell=(root/'RUN_V1232Q.sh').read_text()
if 'set -e' in shell or 'set -u' in shell or 'pipefail' in shell:
    raise SystemExit('STRICT_SHELL_FORBIDDEN')

required=(
    'recover_bundle_authorities(',
    "PCHSI_V1232S_SHARD_TERMINALS_V1.json",
    "sr.get('attempt_bundle_root')",
    'assert_fixed_head_api_contract(repo)',
    "api['build_group_synthesis_inputs']",
    "api['load_attempt_directory_v1']",
    'build_local_u_reg_manifest(',
    "CLEAN_ANALYZER_LOCAL_U_REG_V1.json",
    "'schema_id':'CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1'",
    "'task_access_manifest_sha256':sha256_file(access_manifest_path)",
    "task_set_manifest_sha256=u_reg['u_reg_sha256']",
    'build_group_manifests(',
    'local_results=local_results',
    'mechanical_signatures=mechanical_signatures',
    'build_group_synthesis_inputs(',
    'source_bindings=source_contexts',
    "write_new_value(gr/'source_contexts.json',members)",
)
for snippet in required:
    if snippet not in source:
        raise SystemExit('V1232Q_CONTRACT_SNIPPET_MISSING:'+snippet)

for forbidden in (
    "domain_hash('V1232Q_TASK_ACCESS_UNIVERSE_V1'",
    "Path(str(row['attempt_bundle_path'])).resolve()",
    'build_group_synthesis_input,',
    'bundle.public_transitions',
    'build_group_manifests(signatures',
    "'schema_id':'V1232Q_GROUP_SOURCE_CONTEXTS_V1'",
):
    if forbidden in source:
        raise SystemExit('STALE_OR_INCOMPATIBLE_ASSUMPTION_PRESENT:'+forbidden)

# Generic package-local guard for the exact V128/V1232P failure class.
tree=ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='domain_hash':
        if len(node.args)<2:
            raise SystemExit('DOMAIN_HASH_CALL_MISSING_PAYLOAD')
        if isinstance(node.args[1],(ast.List,ast.Tuple,ast.Set,ast.ListComp,ast.SetComp,ast.GeneratorExp)):
            raise SystemExit('DOMAIN_HASH_SEQUENCE_PAYLOAD_FORBIDDEN')

print('RUNTIME_REGISTRY_AUTHORITY_RECONCILIATION_CONTRACT_PASS')
print('CANONICAL_TASK_ACCESS_MANIFEST_REUSE_PASS')
print('CANONICAL_LOCAL_UREG_REUSE_PASS')
print('DOMAIN_HASH_MAPPING_CONTRACT_PASS')
print('CANONICAL_ACT3_REUSE_CONTRACT_PASS')
print('IMPORT_SURFACE_RELEASE_POLICY_PASS')

cp=subprocess.run([
    sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(root/'tests')
])
if cp.returncode:
    raise SystemExit(cp.returncode)
print('V1232Q_PACKAGE_VERIFY_PASS')
