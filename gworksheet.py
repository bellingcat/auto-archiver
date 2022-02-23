from gspread import utils


class GWorksheet:
    COLUMN_NAMES = {
        'url': 'media url',
        'archive': 'archive location',
        'date': 'archive date',
        'status': 'archive status',
        'thumbnail': 'thumbnail',
        'thumbnail_index': 'thumbnail index',
        'timestamp': 'upload timestamp',
        'title': 'upload title',
        'duration': 'duration'
    }

    def __init__(self, worksheet, columns=COLUMN_NAMES):
        self.wks = worksheet
        self.headers = [v.lower() for v in self.wks.row_values(1)]
        self.columns = columns

    def _check_col_exists(self, col: str):
        if col not in self.columns:
            raise Exception(f'Column {col} is not in the configured column names: {self.columns.keys()}')

    def _col_index(self, col: str):
        self._check_col_exists(col)
        return self.headers.index(self.columns[col])

    def col_exists(self, col: str):
        self._check_col_exists(col)
        return self.columns[col] in self.headers

    def count_rows(self):
        return len(self.wks.get_values())

    def get_row(self, row: int):
        # row is 1-based
        return self.wks.row_values(row)

    def get_cell(self, row, col: str):
        """
        returns the cell value from (row, col), 
        where row can be an index (1-based) OR list of values
        as received from self.get_row(row)
        """
        if type(row) == int:
            row = self.get_row(row)

        col_index = self._col_index(col)
        if col_index >= len(row):
            return ''
        return row[col_index]

    def set_cell(self, row: int, col: str, val):
        # row is 1-based
        col_index = self._col_index(col) + 1
        self.wks.update_cell(row, col_index, val)

    def batch_set_cell(self, cell_updates):
        """
        receives a list of [(row:int, col:str, val)] and batch updates it, the parameters are the same as in the self.set_cell() method
        """
        cell_updates = [
            {
                'range': self.to_a1(row, self._col_index(col) + 1),
                'values': [[val]]
            }
            for row, col, val in cell_updates
        ]
        self.wks.batch_update(cell_updates, value_input_option='USER_ENTERED')

    def to_a1(self, row: int, col: int):
        # row, col are 1-based
        return utils.rowcol_to_a1(row, col)
