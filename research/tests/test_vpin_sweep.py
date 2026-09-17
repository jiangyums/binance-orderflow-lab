from research.vpin_sweep import PARAM_GRID, run_sweep

def test_param_grid_size():
    total = 1
    for v in PARAM_GRID.values():
        total *= len(v)
    assert total == 720

def test_run_sweep_smoke():
    df = run_sweep(max_combos=2)  # quick smoke
    assert 'fpr' in df.columns and 'precision' in df.columns
