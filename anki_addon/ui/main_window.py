import anki.lang
from aqt.qt import (
    pyqtSignal, Qt, QSizePolicy,
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QButtonGroup, QStackedWidget, QComboBox, QScrollArea,
)
from aqt.operations import QueryOp
from aqt.theme import theme_manager
from aqt import mw, colors, gui_hooks

from ..sonaveeb import Sonaveeb
from .word_info import WordInfoPanel

class SonaveebDialog(QWidget):
    def __init__(self, sonaveeb=None, parent=None):
        super().__init__(parent=parent)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setWindowTitle('Sõnaveeb Deck Builder')
        self.resize(600, 800)

        # Add header bar
        # - Add deck selector
        self._deck_selector = QComboBox()
        for deck in mw.col.decks.all_names_and_ids():
            self._deck_selector.addItem(deck.name, userData=deck.id)
        self._deck_selector.currentIndexChanged.connect(self.deck_changed)
        self._deck_selector.setMinimumWidth(300)
        self._deck_selector.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # - Add language selector
        languages = {
            code.split('_')[0]: name.split(' ')[0]
            for name, code in anki.lang.langs
        }
        # - Fix language name typos
        languages['uk'] = 'Українська'
        languages['jbo'] = 'Lojban'
        self._lang_selector = QComboBox()
        for code, lang in languages.items():
            self._lang_selector.addItem(lang, userData=code)
        self._lang_selector.currentIndexChanged.connect(self.language_changed)
        self._lang_selector.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        # - Populate header bar
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel('Deck:'))
        header_layout.addWidget(self._deck_selector)
        header_layout.addStretch(1)
        header_layout.addWidget(QLabel('Translate into:'))
        header_layout.addWidget(self._lang_selector)
        header_layout.setContentsMargins(10, 5, 10, 5)
        self._header_bar = QWidget()
        self._header_bar.setStyleSheet(f'background: {theme_manager.var(colors.CANVAS_ELEVATED)}')
        self._header_bar.setLayout(header_layout)

        self._dict_selector = QComboBox()
        for dict_key in Sonaveeb.DICTIONARY_TYPES:
            display_name = Sonaveeb.DICTIONARY_TYPES[dict_key].name
            self._dict_selector.addItem(display_name, userData=dict_key)
        self._dict_selector.currentIndexChanged.connect(self.dictionary_changed)
        self._dict_selector.setMinimumWidth(100)
        self._dict_selector.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # Add tooltips explaining the differences
        self._dict_selector.setToolTip(
            "lite: Dictionary for language learners\n"
            "unif: Comprehensive dictionary with detailed information"
        )

        # Add to header layout
        header_layout.addWidget(QLabel('Dictionary:'))
        header_layout.addWidget(self._dict_selector)

        # Add search bar
        self._search = QLineEdit()
        self._search.setFocus()
        self._search.returnPressed.connect(self.search_triggered)
        self._search_button = QPushButton('Search')
        self._search_button.clicked.connect(self.search_triggered)
        search_layout = QHBoxLayout()
        search_layout.addWidget(self._search)
        search_layout.addWidget(self._search_button)
        search_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        search_layout.setContentsMargins(10, 5, 10, 5)
        search_bar = QWidget()
        search_bar.setFixedWidth(500)
        search_bar.setLayout(search_layout)

        # Add content UI
        self._form_selector = SelectorRow()
        self._form_selector.selected.connect(self.form_selected)
        self._search_results_layout = QVBoxLayout()
        self._search_results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        search_results_container = QWidget()
        search_results_container.setLayout(self._search_results_layout)
        search_results_container.setMaximumWidth(600)
        search_results_scrollarea = QScrollArea()
        search_results_scrollarea.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        search_results_scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        search_results_scrollarea.setWidget(search_results_container)
        search_results_scrollarea.setWidgetResizable(True)
        # search_results_scrollarea.setStyleSheet('border: 0')
        content_layout = QVBoxLayout()
        content_layout.addWidget(self._form_selector)
        content_layout.addWidget(search_results_scrollarea)
        content_layout.setContentsMargins(0, 0, 0, 0)
        self._content = QWidget()
        self._content.setLayout(content_layout)
        self._status = QLabel()
        self._status.setStyleSheet(f'font-size: 18pt; color: {theme_manager.var(colors.FG_SUBTLE)}')
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_stack = QStackedWidget()
        self._content_stack.addWidget(self._content)
        self._content_stack.addWidget(self._status)
        self._content_stack.setCurrentWidget(self._status)

        report_link = QLabel('See any mistakes or other problems? Please report <a href="https://github.com/azymohliad/anki-sonaveeb/issues">here</a>')
        report_link.setTextFormat(Qt.TextFormat.RichText)
        report_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        report_link.setOpenExternalLinks(True)
        report_link.setStyleSheet(f'font-size: 9pt; color: {theme_manager.var(colors.FG_SUBTLE)}')
        report_link.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        layout = QVBoxLayout()
        layout.addWidget(self._header_bar)
        layout.addWidget(search_bar)
        layout.addWidget(self._content_stack)
        layout.addWidget(report_link)
        layout.setAlignment(search_bar, Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(0, 0, 0, 5)
        self.setLayout(layout)
        self._search.setFocus()
        self.set_status('Search something :)')

        gui_hooks.theme_did_change.append(self.theme_changed)
        self._sonaveeb = sonaveeb or Sonaveeb()

        # Restore config
        self._config = mw.addonManager.getConfig(__name__)
        if deck := self._config.get('deck'):
            self._deck_selector.setCurrentText(deck)
        default_lang = anki.lang.get_def_lang()[1].split('_')[0]
        lang = self._config.get('language', default_lang)
        index_lang = self._lang_selector.findData(lang)
        if index_lang >= 0:
            self._lang_selector.setCurrentIndex(index_lang)

        # Initialize dictionary type from config
        default_dict_type = Sonaveeb.DEFAULT_DICTIONARY
        dict_type = self._config.get('dictionary', default_dict_type)
        index_dict = self._dict_selector.findData(dict_type)
        if index_dict >= 0:
            self._dict_selector.setCurrentIndex(index_dict)
            self._sonaveeb.select_dictionary(dict_type)

    def lang_code(self):
        return self._lang_selector.currentData()

    def deck_id(self):
        return self._deck_selector.currentData()

    def dict_type(self):
        return self._dict_selector.currentData()

    def search_results(self):
        return [
            self._search_results_layout.itemAt(i).widget()
            for i in range(self._search_results_layout.count())
        ]

    def set_status(self, status):
        self._status.setText(status)
        self._content_stack.setCurrentWidget(self._status)

    def clear_search_results(self):
        self._form_selector.clear()
        while self._search_results_layout.count():
            child = self._search_results_layout.takeAt(0)
            child.widget().deleteLater()

    def request_search(self, query):
        self._search_button.setEnabled(False)
        self.set_status('Searching...')
        operation = QueryOp(
            parent=self,
            op=lambda col: self.search_candidates(query),
            success=self.search_results_received
        ).failure(self.handle_search_error)
        operation.run_in_background()

    def search_candidates(self, query):
        match, forms = self._sonaveeb.get_forms(query)
        if match is not None:
            candidates = self._sonaveeb.get_candidates(match)
        else:
            candidates = []
        return candidates, forms

    def search_triggered(self):
        self.clear_search_results()
        query = self._search.text().strip()
        if query != '':
            self.request_search(query)
        else:
            self.set_status('Search something :)')

    def theme_changed(self):
        self._header_bar.setStyleSheet(f'background: {theme_manager.var(colors.CANVAS_ELEVATED)}')

    def form_selected(self, form):
        print(f'Selected form: {form}')
        self._search.setText(form)
        self.search_triggered()

    def language_changed(self, _index):
        lang = self.lang_code()
        for word_panel in self.search_results():
            word_panel.set_translation_language(lang)
        self._config['language'] = lang
        mw.addonManager.writeConfig(__name__, self._config)

    def dictionary_changed(self, _index):
        dict_type = self.dict_type()
        self._sonaveeb.select_dictionary(dict_type)
        self._config['dictionary'] = dict_type
        mw.addonManager.writeConfig(__name__, self._config)
        if self._search.text().strip():
            self.search_triggered()

    def deck_changed(self, _index):
        deck_id = self.deck_id()
        for word_panel in self.search_results():
            word_panel.set_deck(deck_id)
        self._config['deck'] = self._deck_selector.currentText()
        mw.addonManager.writeConfig(__name__, self._config)

    def search_results_received(self, result):
        candidates, forms = result
        self._search_button.setEnabled(True)
        if len(candidates) == 0:
            if len(forms) == 0:
                self.set_status('Not found :(')
            elif len(forms) == 1:
                self.request_search(forms[0])
            else:
                self._form_selector.set_label('Select base form:')
                self._form_selector.set_options(forms)
                self._form_selector.show()
                self._content_stack.setCurrentWidget(self._content)
        else:
            self._form_selector.set_options(forms)
            self._form_selector.set_label('See also:')
            self._form_selector.setVisible(len(forms) > 0)
            self._content_stack.setCurrentWidget(self._content)
            for homonym in candidates:
                word_panel = WordInfoPanel(homonym, self._sonaveeb, self.deck_id(), self.lang_code())
                self._search_results_layout.addWidget(word_panel)

    def handle_search_error(self, error):
        print(error)
        self.set_status('Search failed :(')
        self._search_button.setEnabled(True)




class SelectorRow(QWidget):
    selected = pyqtSignal(str)
    selected_index = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._buttons = QButtonGroup()
        self._buttons.idToggled.connect(self._button_toggled)
        self._label = QLabel()
        self._layout = QHBoxLayout()
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layout.addWidget(self._label)
        self.setLayout(self._layout)

    def set_label(self, label):
        self._label.setText(label)

    def set_options(self, options):
        self.clear()
        for i, option in enumerate(options):
            button = QPushButton(option)
            button.setFlat(True)
            button.setCheckable(True)
            # button.setChecked(i == 0)
            self._buttons.addButton(button, i)
            self._layout.addWidget(button)

    def clear(self):
        for button in self._buttons.buttons():
            self._buttons.removeButton(button)
            self._layout.removeWidget(button)
            button.deleteLater()

    def _button_toggled(self, index, checked):
        if checked:
            self.selected.emit(self._buttons.button(index).text())
            self.selected_index.emit(index)
