# Note this isn't a feeder, but contained as utility of the gsheet feeder module
import pytest

from auto_archiver.modules.gsheet_feeder_db import GWorksheet


class TestGWorksheet:
    @pytest.fixture
    def mock_worksheet(self, mocker):
        mock_ws = mocker.MagicMock()
        mock_ws.get_values.return_value = [
            ["Link", "Archive Status", "Archive Location", "Archive Date"],
            ["url1", "archived", "filepath1", "2023-01-01"],
            ["url2", "pending", "filepath2", "2023-01-02"],
        ]
        return mock_ws

    @pytest.fixture
    def gworksheet(self, mock_worksheet):
        return GWorksheet(mock_worksheet)

    # Test initialization and basic properties
    def test_initialization_sets_headers(self, gworksheet):
        assert gworksheet.headers == ["link", "archive status", "archive location", "archive date"]

    def test_count_rows_returns_correct_value(self, gworksheet):
        # inc header row
        assert gworksheet.count_rows() == 3

    # Test column validation and lookup
    @pytest.mark.parametrize(
        "col,expected_index",
        [
            ("url", 0),
            ("status", 1),
            ("archive", 2),
            ("date", 3),
        ],
    )
    def test_col_index_returns_correct_index(self, gworksheet, col, expected_index):
        assert gworksheet._col_index(col) == expected_index

    def test_check_col_exists_raises_for_invalid_column(self, gworksheet):
        with pytest.raises(Exception, match="Column invalid_col"):
            gworksheet._check_col_exists("invalid_col")

    # Test data retrieval
    @pytest.mark.parametrize(
        "row,expected",
        [
            (1, ["Link", "Archive Status", "Archive Location", "Archive Date"]),
            (2, ["url1", "archived", "filepath1", "2023-01-01"]),
            (3, ["url2", "pending", "filepath2", "2023-01-02"]),
        ],
    )
    def test_get_row_returns_correct_data(self, gworksheet, row, expected):
        assert gworksheet.get_row(row) == expected

    @pytest.mark.parametrize(
        "row,col,expected",
        [
            (2, "url", "url1"),
            (2, "status", "archived"),
            (3, "date", "2023-01-02"),
        ],
    )
    def test_get_cell_returns_correct_value(self, gworksheet, row, col, expected):
        assert gworksheet.get_cell(row, col) == expected

    def test_get_cell_handles_fresh_data(self, mock_worksheet, gworksheet):
        mock_worksheet.cell.return_value.value = "fresh_value"
        result = gworksheet.get_cell(2, "url", fresh=True)
        assert result == "fresh_value"
        mock_worksheet.cell.assert_called_once_with(2, 1)

    # Test edge cases and error handling
    @pytest.mark.parametrize(
        "when_empty,expected",
        [
            (True, "default"),
            (False, ""),
        ],
    )
    def test_get_cell_or_default_handles_empty_values(
        self, mock_worksheet, when_empty, expected
    ):
        mock_worksheet.get_values.return_value[1][0] = ""  # Empty URL cell
        g = GWorksheet(mock_worksheet)
        assert (
            g.get_cell_or_default(
                2, "url", default="default", when_empty_use_default=when_empty
            )
            == expected
        )

    def test_get_cell_or_default_handles_missing_columns(self, gworksheet):
        assert (
            gworksheet.get_cell_or_default(1, "invalid_col", default="safe") == "safe"
        )

    # Test write operations
    def test_set_cell_updates_correct_position(self, mock_worksheet, gworksheet):
        gworksheet.set_cell(2, "url", "new_url")
        mock_worksheet.update_cell.assert_called_once_with(2, 1, "new_url")

    def test_batch_set_cell_formats_requests_correctly(
        self, mock_worksheet, gworksheet
    ):
        updates = [(2, "url", "new_url"), (3, "status", "processed")]
        gworksheet.batch_set_cell(updates)
        expected_batch = [
            {"range": "A2", "values": [["new_url"]]},
            {"range": "B3", "values": [["processed"]]},
        ]
        mock_worksheet.batch_update.assert_called_once_with(
            expected_batch, value_input_option="USER_ENTERED"
        )

    def test_batch_set_cell_truncates_long_values(self, mock_worksheet, gworksheet):
        long_value = "x" * 50000
        gworksheet.batch_set_cell([(1, "url", long_value)])
        submitted_value = mock_worksheet.batch_update.call_args[0][0][0]["values"][0][0]
        assert len(submitted_value) == 49999

    # Test coordinate conversion
    @pytest.mark.parametrize(
        "row,col,expected",
        [
            (1, "url", "A1"),
            (2, "status", "B2"),
            (3, "archive", "C3"),
            (4, "date", "D4"),
        ],
    )
    def test_to_a1_conversion(self, gworksheet, row, col, expected):
        assert gworksheet.to_a1(row, col) == expected

    # Test empty worksheet
    def test_empty_worksheet_initialization(self, mocker):
        mock_ws = mocker.MagicMock()
        mock_ws.get_values.return_value = []
        g = GWorksheet(mock_ws)
        assert g.headers == []
        assert g.count_rows() == 0
