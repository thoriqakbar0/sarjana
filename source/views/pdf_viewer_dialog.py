from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QPointF, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QToolBar, QPushButton, QSpinBox, QComboBox, QTextEdit,
    QLineEdit, QMenu, QProgressBar, QLabel, QTreeView
)
from PySide6.QtPdf import QPdfDocument, QPdfSearchModel, QPdfBookmarkModel
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

class NavigationToolBar(QToolBar):
    """Toolbar for PDF navigation"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        # Page navigation
        self.prev_btn = QPushButton("←")
        self.next_btn = QPushButton("→")
        self.page_spinbox = QSpinBox()
        self.total_pages = QLabel("/ 0")
        
        self.addWidget(self.prev_btn)
        self.addWidget(self.page_spinbox)
        self.addWidget(self.total_pages)
        self.addWidget(self.next_btn)

        # Zoom controls
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["50%", "75%", "100%", "125%", "150%", "200%"])
        self.zoom_combo.setCurrentText("100%")
        self.addWidget(self.zoom_combo)

class SearchToolBar(QToolBar):
    """Toolbar for search functionality"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.search_model = None  # Will be set by parent
        self.current_result_index = -1

    def setup_ui(self):
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.addWidget(self.search_input)

        self.prev_result = QPushButton("↑")
        self.next_result = QPushButton("↓")
        self.addWidget(self.prev_result)
        self.addWidget(self.next_result)
        
        # Connect search signals
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.prev_result.clicked.connect(self._search_backward)
        self.next_result.clicked.connect(self._search_forward)

    def set_search_model(self, model: QPdfSearchModel):
        """Set the search model to use"""
        self.search_model = model

    def _search_backward(self):
        """Navigate to previous search result"""
        if not self.search_model:
            return
            
        count = self.search_model.rowCount()
        if count == 0:
            return
            
        self.current_result_index = (self.current_result_index - 1) % count
        self._go_to_current_result()

    def _search_forward(self):
        """Navigate to next search result"""
        if not self.search_model:
            return
            
        count = self.search_model.rowCount()
        if count == 0:
            return
            
        self.current_result_index = (self.current_result_index + 1) % count
        self._go_to_current_result()

    def _on_search_text_changed(self, text: str):
        """Update search model with new text"""
        if self.search_model:
            self.search_model.setSearchText(text)
            self.current_result_index = 0 if self.search_model.rowCount() > 0 else -1
            self._go_to_current_result()

    def _go_to_current_result(self):
        """Navigate to current search result"""
        if self.current_result_index >= 0:
            result = self.search_model.resultAtIndex(self.current_result_index)
            if result and hasattr(self.parent(), '_goto_page'):
                self.parent()._goto_page(result.page() + 1)

class PdfViewerDialog(QWidget):
    """Enhanced PDF viewer with sidebar, search and annotations"""
    
    def __init__(self, path: Path):
        super().__init__()
        self.setWindowTitle("Research Paper Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main layout with three panels
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        
        # Main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)
        
        # Center panel - PDF Viewer
        self.pdf_container = QWidget()
        pdf_layout = QVBoxLayout()
        self.pdf_container.setLayout(pdf_layout)
        
        # Toolbars
        self.navigation_toolbar = NavigationToolBar()
        self.search_toolbar = SearchToolBar(self)
        pdf_layout.addWidget(self.navigation_toolbar)
        pdf_layout.addWidget(self.search_toolbar)
        
        # PDF View with enhanced features
        self.pdf_view = QPdfView()
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.pdf_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.pdf_view.customContextMenuRequested.connect(self._show_context_menu)
        pdf_layout.addWidget(self.pdf_view)
        
        # Right panel - Chat, Summary, Highlights
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Summary section
        self.summary = QTextEdit()
        self.summary.setPlaceholderText("Document Summary")
        self.summary.setMaximumHeight(200)
        right_layout.addWidget(self.summary)
        
        # Highlights section
        self.highlights = QTextEdit()
        self.highlights.setPlaceholderText("Highlights")
        self.highlights.setMaximumHeight(200)
        right_layout.addWidget(self.highlights)
        
        # Chat section
        self.chat_display = QTextEdit()
        self.chat_display.setPlaceholderText("Chat History")
        self.chat_display.setReadOnly(True)
        right_layout.addWidget(self.chat_display)
        
        # Chat input
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Type your message...")
        self.chat_input.setMaximumHeight(100)
        right_layout.addWidget(self.chat_input)
        
        self.send_btn = QPushButton("Send")
        right_layout.addWidget(self.send_btn)
        
        # Add panels to splitter
        self.main_splitter.addWidget(self.pdf_container)
        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setStretchFactor(0, 2)  # PDF viewer gets more space
        self.main_splitter.setStretchFactor(1, 1)
        
        # Document handling
        self.document = QPdfDocument()
        self.search_model = QPdfSearchModel()
        self.search_model.setDocument(self.document)
        self.pdf_view.setDocument(self.document)
        self._pdf_path = path
        
        # Connect signals
        self.navigation_toolbar.prev_btn.clicked.connect(self._previous_page)
        self.navigation_toolbar.next_btn.clicked.connect(self._next_page)
        self.navigation_toolbar.page_spinbox.valueChanged.connect(self._goto_page)
        self.navigation_toolbar.zoom_combo.currentTextChanged.connect(self._zoom_changed)
        
        # Load document
        self.load_pdf()
        
        # Add table of contents panel
        self.toc_widget = QTreeView()
        self.bookmark_model = QPdfBookmarkModel()
        self.bookmark_model.setDocument(self.document)
        self.toc_widget.setModel(self.bookmark_model)
        
        # Connect TOC selection
        self.toc_widget.clicked.connect(self._on_toc_clicked)
        
        # Initialize search model before creating toolbar
        self.search_model = QPdfSearchModel()
        self.search_model.setDocument(self.document)
        
        # Create toolbar and set search model
        self.search_toolbar = SearchToolBar(self)
        self.search_toolbar.set_search_model(self.search_model)
        
        # Remove the currentResultChanged connection since it's not available
        # self.search_model.currentResultChanged.connect(self._on_search_result_changed)
        
        # ... rest of initialization code ...

    def load_pdf(self):
        """Load the PDF document"""
        try:
            self.document.load(str(self._pdf_path))
            total_pages = self.document.pageCount()
            self.navigation_toolbar.page_spinbox.setRange(1, total_pages)
            self.navigation_toolbar.total_pages.setText(f"/ {total_pages}")
            self.navigation_toolbar.page_spinbox.setValue(1)
        except Exception as e:
            print(f"Error loading PDF: {e}")

    def _previous_page(self):
        current = self.navigation_toolbar.page_spinbox.value()
        if current > 1:
            self.navigation_toolbar.page_spinbox.setValue(current - 1)

    def _next_page(self):
        current = self.navigation_toolbar.page_spinbox.value()
        if current < self.document.pageCount():
            self.navigation_toolbar.page_spinbox.setValue(current + 1)

    def _goto_page(self, page_num: int):
        if 1 <= page_num <= self.document.pageCount():
            self.pdf_view.pageNavigator().jump(page_num - 1, QPointF())

    def _zoom_changed(self, zoom_text: str):
        zoom = float(zoom_text.rstrip('%')) / 100.0
        self.pdf_view.setZoomFactor(zoom)

    def _show_context_menu(self, pos):
        """Show context menu for text operations"""
        menu = QMenu(self)
        
        # Get selected text directly when menu is shown
        selected_text = self.pdf_view.selectedText()
        
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self._copy_selected_text)
        copy_action.setEnabled(bool(selected_text))  # Enable only if text is selected
        menu.addAction(copy_action)
        
        highlight_action = QAction("Highlight", self)
        highlight_action.triggered.connect(self._highlight_selected_text)
        highlight_action.setEnabled(bool(selected_text))  # Enable only if text is selected
        menu.addAction(highlight_action)
        
        menu.exec_(self.pdf_view.mapToGlobal(pos))

    def _copy_selected_text(self):
        """Copy selected text to clipboard"""
        text = self.pdf_view.selectedText()
        if text:
            QApplication.clipboard().setText(text)

    def _highlight_selected_text(self):
        # TODO: Implement highlight functionality
        pass

    def _on_toc_clicked(self, index):
        # Get page number from bookmark model
        page = self.bookmark_model.data(index, QPdfBookmarkModel.PageNumberRole)
        if page is not None:
            self._goto_page(page + 1)  # +1 because page numbers are 0-based internally
