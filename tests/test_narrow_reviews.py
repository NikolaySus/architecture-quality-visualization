"""Scientific boundary cases introduced by the narrower classification."""
from collections import Counter
from narrow_review import *

def test_frozen_cohort_and_exact_partitions():
 assert len(MM)==56 and len(OBS)==43
 assert Counter(OP[mid] for mid in MM)=={'O1':3,'O2':34,'O3':19}
 for cfg in CONFIGS:
  assert Counter(mid for c in cells(cfg) for mid in c['method_ids'])==Counter(list(MM))
  assert Counter(mid for _,ids in feature_profiles(cfg)[1] for mid in ids)==Counter(list(MM))

def test_candidate_execution_and_signal_are_not_estimator_execution():
 for mid in ['M44','M45','M46','M47','M48','M49','M54']:
  assert ROWS[mid]['signal_profile']=='G'
  assert ROWS[mid]['operation']=='graph'
 assert ROWS['M25']['signal_profile']=='A'  # FlexiBERT head hooks are outputs.
 assert ROWS['M15']['signal_profile']=='D'  # EZNAS takes gradients, not weights.
 assert ROWS['M08']['signal_profile']=='AD' # Fisher directly uses activations.
 assert ROWS['M32']['operation']=='derivatives'
 assert ROWS['M32']['synthetic_component'] and ROWS['M32']['use_inputs']=='unlabeled'
 assert ROWS['M37']['signal_profile']=='GWAD' # Full ZCP includes static sizes.

def test_preparation_does_not_leak_into_candidate_inputs():
 assert ROWS['M26']['setup']=='calibration' and ROWS['M27']['setup']=='distribution'
 assert ROWS['M26']['use_inputs']==ROWS['M27']['use_inputs']=='no_examples'
 assert ROWS['M47']['setup']=='prompt'
 assert ROWS['M52']['setup']==ROWS['M54']['setup']=='curves'
 assert ROWS['M35']['use_inputs']=='synthetic'
 assert ROWS['M51']['setup']=='distribution'
 assert ROWS['M44']['representation']==ROWS['M45']['representation']=='architecture_pretrain'
 assert ROWS['M49']['representation']=='frozen_lm'

def test_variant_specific_numeric_access_and_primary_evidence():
 for mid in ['M04','M20','M21']:
  o=next(o for o in OBS if o['method_id']==mid and o['block']=='G1')
  assert access(o,MM)=='unlabeled'
  assert MM[mid]['data_access_at_use']=='none'
 for mid in ['M05','M06','M07','M08','M12']:
  o=next(o for o in OBS if o['method_id']==mid and o['block']=='G1')
  assert access(o,MM)=='unlabeled'
 assert MM['M33']['data_access_at_use']==MM['M34']['data_access_at_use']=='labeled_or_objective'
 assert Counter(m['data_access_at_use'] for m in METHODS)==dict(none=26,unlabeled=16,labeled_or_objective=14)
 for mid,key in [('M15','LPZ_EZNAS'),('M25','LPZ_HEAD'),('M32','DEXTR_CODE'),('M70','LPZ_L2')]:
  assert key in ROWS[mid]['evidence']
  assert len(AUDIT['sources'][key]['sha256'])==64
