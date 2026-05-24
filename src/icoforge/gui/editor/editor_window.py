"""Main editor window for editing ICO files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from icoforge.core.ico_reader import read_ico
from icoforge.core.models import SizeSpec
from icoforge.gui.editor.canvas import ZOOM_LEVELS, EditorCanvas
from icoforge.gui.editor.tools import EraserTool, EyedropperTool, PixelTool, Tool

if TYPE_CHECKING:
    from PIL import Image


class EditorWindow(QMainWindow):
    """Main window for the pixel editor."""

    def __init__(self, ico_path: Path, parent: object | None = None) -> None:
        super().__init__(parent)
        self.ico_path = ico_path
        self.setWindowTitle(f"Editor - {ico_path.name}")
        self.resize(1000, 700)

        # Frames data: list of (Image, SizeSpec) tuples
        self._frames: list[tuple[Image.Image, SizeSpec]] = []
        self._current_frame_index = 0

        # Tool state
        self._current_color: tuple[int, int, int, int] = (0, 0, 0, 255)
        self._current_size = 1
        self._tools: dict[str, Tool] = {}

        # Zoom state: remember user-set zoom per icon size key (w, h)
        self._zoom_overrides: dict[tuple[int, int], float] = {}
        self._user_set_zoom = False

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create splitter: left = size list, right = canvas
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left panel: size list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_layout.addWidget(QLabel("Rozmiary:"))

        self._size_list = QListWidget()
        self._size_list.itemClicked.connect(self._on_size_selected)
        left_layout.addWidget(self._size_list)

        splitter.addWidget(left_widget)
        splitter.setStretchFactor(0, 1)

        # Right panel: canvas
        self._canvas = EditorCanvas()
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        splitter.addWidget(self._canvas)
        splitter.setStretchFactor(1, 3)

        # Toolbar
        self._setup_toolbar()

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

        # Load ICO file
        self._load_ico(ico_path)

    def _setup_toolbar(self) -> None:
        """Setup the drawing toolbar."""
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)

        # Pencil tool
        pencil_action = QAction("Pencil (B)", self)
        pencil_action.triggered.connect(self._on_tool_pencil)
        pencil_action.setShortcut("B")
        toolbar.addAction(pencil_action)

        # Eraser tool
        eraser_action = QAction("Eraser (E)", self)
        eraser_action.triggered.connect(self._on_tool_eraser)
        eraser_action.setShortcut("E")
        toolbar.addAction(eraser_action)

        # Eyedropper tool
        eyedropper_action = QAction("Eyedropper (I)", self)
        eyedropper_action.triggered.connect(self._on_tool_eyedropper)
        eyedropper_action.setShortcut("I")
        toolbar.addAction(eyedropper_action)

        toolbar.addSeparator()

        # Color picker
        color_action = QAction("Pick Color", self)
        color_action.triggered.connect(self._on_pick_color)
        toolbar.addAction(color_action)

        toolbar.addSeparator()

        # Size control
        toolbar.addWidget(QLabel("Size:"))
        self._size_spinbox = QSpinBox()
        self._size_spinbox.setMinimum(1)
        self._size_spinbox.setMaximum(8)
        self._size_spinbox.setValue(1)
        self._size_spinbox.valueChanged.connect(self._on_size_changed)
        toolbar.addWidget(self._size_spinbox)

        # Zoom toolbar
        zoom_toolbar = QToolBar("Zoom")
        self.addToolBar(zoom_toolbar)

        zoom_out_action = QAction("- Zoom Out", self)
        zoom_out_action.triggered.connect(self._on_zoom_out)
        zoom_out_action.setShortcut(QKeySequence("-"))
        zoom_toolbar.addAction(zoom_out_action)

        fit_action = QAction("Fit", self)
        fit_action.triggered.connect(self._on_zoom_fit)
        fit_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_toolbar.addAction(fit_action)

        one_to_one_action = QAction("1:1", self)
        one_to_one_action.triggered.connect(self._on_zoom_1to1)
        one_to_one_action.setShortcut(QKeySequence("Ctrl+1"))
        zoom_toolbar.addAction(one_to_one_action)

        zoom_in_action = QAction("+ Zoom In", self)
        zoom_in_action.triggered.connect(self._on_zoom_in)
        zoom_in_action.setShortcut(QKeySequence("="))
        zoom_toolbar.addAction(zoom_in_action)

        zoom_toolbar.addSeparator()

        self._zoom_combo = QComboBox()
        self._zoom_combo.setMinimumWidth(80)
        for level in ZOOM_LEVELS:
            self._zoom_combo.addItem(f"{int(level * 100)}%", level)
        self._zoom_combo.currentIndexChanged.connect(self._on_zoom_combo_changed)
        zoom_toolbar.addWidget(self._zoom_combo)

    def _load_ico(self, path: Path) -> None:
        """Load an ICO file and populate the UI."""
        try:
            self._frames = read_ico(path)

            # Populate size list
            self._size_list.clear()
            for i, (_image, spec) in enumerate(self._frames):
                size_str = f"{spec.width}x{spec.height}"
                item = QListWidgetItem(size_str)
                item.setData(Qt.ItemDataRole.UserRole, i)
                # Make font monospace for alignment
                font = QFont("Courier")
                item.setFont(font)
                self._size_list.addItem(item)

            # Select first frame
            if self._frames:
                self._size_list.setCurrentRow(0)
                self._on_size_selected(self._size_list.item(0))

            self._status_bar.showMessage(f"Loaded ICO: {len(self._frames)} sizes")
        except Exception as e:
            self._status_bar.showMessage(f"Error loading ICO: {e}")

    def _on_size_selected(self, item: QListWidgetItem) -> None:
        """Handle size selection from list."""
        frame_index = item.data(Qt.ItemDataRole.UserRole)
        if frame_index is not None and 0 <= frame_index < len(self._frames):
            self._current_frame_index = frame_index
            image, spec = self._frames[frame_index]
            size_key = (spec.width, spec.height)

            # Load image — auto_zoom only when no user override for this size
            has_override = size_key in self._zoom_overrides
            self._user_set_zoom = False
            self._canvas.load_image(image, auto_zoom=not has_override)

            if has_override:
                self._canvas._apply_zoom(self._zoom_overrides[size_key])

            self.setWindowTitle(f"Editor - {self.ico_path.name} [{spec.width}x{spec.height}]")

            self._tools = {}
            self._on_tool_pencil()

            self._status_bar.showMessage(
                f"Editing {spec.width}x{spec.height} ({frame_index + 1}/{len(self._frames)})"
            )

    def _on_zoom_changed(self, zoom: float) -> None:
        """Handle zoom level change."""
        percentage = int(zoom * 100)
        self._status_bar.showMessage(f"Zoom: {percentage}%")

        # Update combo box selection without triggering another zoom change
        self._zoom_combo.blockSignals(True)
        best_idx = 0
        best_diff = float("inf")
        for i in range(self._zoom_combo.count()):
            level = self._zoom_combo.itemData(i)
            diff = abs(level - zoom)
            if diff < best_diff:
                best_diff = diff
                best_idx = i
        self._zoom_combo.setCurrentIndex(best_idx)
        self._zoom_combo.blockSignals(False)

        # Remember user zoom if this was triggered by a user action
        if self._user_set_zoom and self._current_frame_index < len(self._frames):
            _, spec = self._frames[self._current_frame_index]
            self._zoom_overrides[(spec.width, spec.height)] = zoom

    def _create_tools(self) -> None:
        """Create tool instances for current frame."""
        if self._canvas._current_image is None:
            return
        image = self._canvas._current_image
        self._tools = {
            "pencil": PixelTool(image, self._current_color, self._current_size),
            "eraser": EraserTool(image, self._current_size),
            "eyedropper": EyedropperTool(image),
        }

    def _on_tool_pencil(self) -> None:
        """Switch to pencil tool."""
        if "pencil" not in self._tools:
            self._create_tools()
        tool = self._tools["pencil"]
        assert isinstance(tool, PixelTool)
        tool.set_color(self._current_color)
        tool.set_size(self._current_size)
        self._canvas.set_tool(tool)
        self._status_bar.showMessage("Tool: Pencil")

    def _on_tool_eraser(self) -> None:
        """Switch to eraser tool."""
        if "eraser" not in self._tools:
            self._create_tools()
        tool = self._tools["eraser"]
        assert isinstance(tool, EraserTool)
        tool.set_size(self._current_size)
        self._canvas.set_tool(tool)
        self._status_bar.showMessage("Tool: Eraser")

    def _on_tool_eyedropper(self) -> None:
        """Switch to eyedropper tool."""
        if "eyedropper" not in self._tools:
            self._create_tools()
        tool = self._tools["eyedropper"]
        self._canvas.set_tool(tool)
        self._status_bar.showMessage("Tool: Eyedropper (click to pick color)")

    def _on_pick_color(self) -> None:
        """Open color picker dialog."""
        color = QColorDialog.getColor(
            QColor(*self._current_color),
            self,
            "Pick Color",
        )
        if color.isValid():
            self._current_color = (
                color.red(),
                color.green(),
                color.blue(),
                color.alpha(),
            )
            if "pencil" in self._tools:
                tool = self._tools["pencil"]
                assert isinstance(tool, PixelTool)
                tool.set_color(self._current_color)
            self._status_bar.showMessage(
                f"Color: #{color.red():02x}{color.green():02x}{color.blue():02x}"
            )

    def _on_zoom_in(self) -> None:
        self._user_set_zoom = True
        self._canvas.zoom_in()

    def _on_zoom_out(self) -> None:
        self._user_set_zoom = True
        self._canvas.zoom_out()

    def _on_zoom_fit(self) -> None:
        self._user_set_zoom = True
        self._canvas.fit_to_window()

    def _on_zoom_1to1(self) -> None:
        self._user_set_zoom = True
        self._canvas.zoom_1to1()

    def _on_zoom_combo_changed(self, index: int) -> None:
        """Handle zoom level selected from combo box."""
        level = self._zoom_combo.itemData(index)
        if level is not None:
            self._user_set_zoom = True
            self._canvas._apply_zoom(float(level))

    def _on_size_changed(self, value: int) -> None:
        """Handle brush size change."""
        self._current_size = value
        if "pencil" in self._tools:
            tool = self._tools["pencil"]
            assert isinstance(tool, PixelTool)
            tool.set_size(value)
        if "eraser" in self._tools:
            tool = self._tools["eraser"]
            assert isinstance(tool, EraserTool)
            tool.set_size(value)
        self._status_bar.showMessage(f"Brush size: {value}px")
