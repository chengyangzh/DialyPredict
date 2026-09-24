from dialypredict.modeling import HDF_TASK, SPKTV_TASK


def test_spktv_contract_has_adjustable_variables() -> None:
    constraints = dict(zip(SPKTV_TASK.features, SPKTV_TASK.monotone_vector(), strict=True))
    assert constraints["qb_prescribed"] == 1
    assert constraints["actual_duration"] == 1
    assert constraints["post_weight"] == 0


def test_hdf_has_separate_endpoint() -> None:
    assert HDF_TASK.target == "total_convective_volume"
    assert HDF_TASK.target != SPKTV_TASK.target
