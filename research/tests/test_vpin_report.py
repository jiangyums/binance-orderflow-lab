from pathlib import Path

def test_report_generates():
    from research.vpin_report import generate_report
    generate_report(data_dir="data/hist/vpin", out_path="data/hist/vpin/report_test.md")
    assert Path("data/hist/vpin/report_test.md").exists()
