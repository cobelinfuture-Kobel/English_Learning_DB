from functools import lru_cache
from ulga.builders import build_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck as builder
from ulga.validators import validate_a1fs_v1_u02sa01_unit01_unit02_cumulative_sentence_asset_coverage_recheck as validator
@lru_cache(maxsize=1)
def report():
    candidate=builder.build_candidate(); approved=builder.admit_candidate(candidate); result=validator.validate_approved(candidate,approved); assert result["error_count"]==0; return approved["payload"]
