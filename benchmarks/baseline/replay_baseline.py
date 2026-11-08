import importlib.util
import runpy
from pathlib import Path
import pkg_re.operations
import pkg_re.batch_review
import pkg_re.net_review
base=Path(__file__).resolve().parent
for name, filename in [('pkg_re.engine.baseline_repairs','baseline-repairs.py'),('pkg_re.baseline_net_review','baseline-net_review.py')]:
 spec=importlib.util.spec_from_file_location(name,base/filename)
 module=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(module)
 if filename=='baseline-repairs.py':
  pkg_re.operations.propose_repairs=module.propose_repairs
 else:
  pkg_re.batch_review.refresh_recommendations=module.refresh_recommendations
  pkg_re.net_review.refresh_recommendations=module.refresh_recommendations
runpy.run_path(str(base/'damage_probe.py'))
