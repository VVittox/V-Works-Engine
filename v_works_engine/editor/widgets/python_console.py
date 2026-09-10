from __future__ import annotations
import contextlib, io, traceback
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

class PythonConsoleWidget(QWidget):

    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.env = {'editor': editor}
        lay = QVBoxLayout(self)
        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.appendPlainText('V Works Python Console\nVariables: editor, scene, selected, project\n')
        lay.addWidget(self.out, 1)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText('Python expression / statement')
        self.input.returnPressed.connect(self.execute)
        run = QPushButton('Run')
        run.clicked.connect(self.execute)
        row.addWidget(self.input, 1)
        row.addWidget(run)
        lay.addLayout(row)

    def execute(self):
        code = self.input.text().strip()
        if not code:
            return
        self.input.clear()
        self.out.appendPlainText(f'>>> {code}')
        self.env.update(scene=self.editor.document.scene, selected=self.editor.selected, project=self.editor.project)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                try:
                    r = eval(code, self.env, self.env)
                except SyntaxError:
                    exec(code, self.env, self.env)
                    r = None
            text = buf.getvalue()
            if text:
                self.out.appendPlainText(text.rstrip())
            if r is not None:
                self.out.appendPlainText(repr(r))
        except Exception:
            self.out.appendPlainText(traceback.format_exc())
