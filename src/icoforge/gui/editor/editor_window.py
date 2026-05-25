"""Main editor window for editing ICO files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
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
from icoforge.gui.editor.palette import PaletteWidget
from icoforge.gui.editor.tools import (
    EraserTool,
    EyedropperTool,
    FillTool,
    LineTool,
    PixelTool,
    RectTool,
    SelectTool,
    Tool,
)

if TYPE_CHECKING:
    from PIL import Image


class EditorWindow(QMainWindow):
    """Main window for the pixel editor."""

    def __init__(self, ico_path: Path, parent: object | None = None) -> None:
        super().__init__(parent)
        self.ico_path = ico_path
        self.setWindowTitle(f"Editor - {ico_path.name}")
        self.resize(1000, 700)

        # Frames data
        self._frames: list[tuple[Image.Image, SizeSpec]] = []
        self._current_frame_index = 0

        # Tool state
        self._current_size = 1
        self._current_tool_name: str = "pencil"
        self._current_tolerance: int = 32
        self._rect_filled: bool = False
        self._tools: dict[str, Tool] = {}

        # Clipboard for SelectTool copy/cut/paste
        self._clipboard: Image.Image | None = None
        self._clipboard_origin: tuple[int, int] = (0, 0)

        # Zoom state: remember user-set zoom per icon size key (w, h)
        self._zoom_overrides: dict[tuple[int, int], float] = {}
        self._user_set_zoom = False

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left panel: palette + size list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)

        self._palette = PaletteWidget()
        self._palette.color_changed.connect(self._on_color_changed)
        self._palette.extract_requested.connect(self._on_extract_requested)
        left_layout.addWidget(self._palette, alignment=Qt.AlignmentFlag.AlignHCenter)

        left_layout.addWidget(QLabel("Rozmiary:"))

        self._size_list = QListWidget()
        self._size_list.itemClicked.connect(self._on_size_selected)
        left_layout.addWidget(self._size_list)

        splitter.addWidget(left_widget)
        splitter.setStretchFactor(0, 1)

        # Right panel: canvas
        self._canvas = EditorCanvas()
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.color_sampled.connect(self._on_color_sampled)
        splitter.addWidget(self._canvas)
        splitter.setStretchFactor(1, 3)

        self._setup_menu()
        self._setup_toolbar()

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

        self._load_ico(ico_path)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_menu(self) -> None:
        """Setup menu bar: Edit with Undo/Redo and Cut/Copy/Paste."""
        edit_menu = self.menuBar().addMenu("&Edit")

        undo_action = self._canvas.undo_stack.createUndoAction(self, "Undo:")
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        edit_menu.addAction(undo_action)

        redo_action = self._canvas.undo_stack.createRedoAction(self, "Redo:")
        redo_action.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setToolTip("Copy selection (Ctrl+C)")
        copy_action.triggered.connect(self._on_copy)
        edit_menu.addAction(copy_action)

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.setToolTip("Cut selection to clipboard (Ctrl+X)")
        cut_action.triggered.connect(self._on_cut)
        edit_menu.addAction(cut_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.setToolTip("Paste from clipboard, sprite-aware (Ctrl+V)")
        paste_action.triggered.connect(self._on_paste)
        edit_menu.addAction(paste_action)

    def _setup_toolbar(self) -> None:
        """Setup drawing toolbar with all tools and per-tool option widgets."""
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)

        # --- Drawing tools ---
        pencil_action = QAction("Pencil (B)", self)
        pencil_action.setToolTip("Freehand drawing (B)")
        pencil_action.triggered.connect(self._on_tool_pencil)
        pencil_action.setShortcut("B")
        toolbar.addAction(pencil_action)

        eraser_action = QAction("Eraser (E)", self)
        eraser_action.setToolTip("Make pixels transparent (E)")
        eraser_action.triggered.connect(self._on_tool_eraser)
        eraser_action.setShortcut("E")
        toolbar.addAction(eraser_action)

        eyedropper_action = QAction("Eyedropper (I)", self)
        eyedropper_action.setToolTip("Pick colour from canvas (I)")
        eyedropper_action.triggered.connect(self._on_tool_eyedropper)
        eyedropper_action.setShortcut("I")
        toolbar.addAction(eyedropper_action)

        fill_action = QAction("Fill (G)", self)
        fill_action.setToolTip("Flood fill with tolerance (G)")
        fill_action.triggered.connect(self._on_tool_fill)
        fill_action.setShortcut("G")
        toolbar.addAction(fill_action)

        line_action = QAction("Line (L)", self)
        line_action.setToolTip("Straight line, Bresenham algorithm (L)")
        line_action.triggered.connect(self._on_tool_line)
        line_action.setShortcut("L")
        toolbar.addAction(line_action)

        rect_action = QAction("Rect (R)", self)
        rect_action.setToolTip("Rectangle - outline or filled (R)")
        rect_action.triggered.connect(self._on_tool_rect)
        rect_action.setShortcut("R")
        toolbar.addAction(rect_action)

        select_action = QAction("Select (S)", self)
        select_action.setToolTip("Rectangular selection - marching ants, Ctrl+C/X/V (S)")
        select_action.triggered.connect(self._on_tool_select)
        select_action.setShortcut("S")
        toolbar.addAction(select_action)

        toolbar.addSeparator()

        # --- Colour shortcuts ---
        swap_action = QAction("Swap Colors (X)", self)
        swap_action.setToolTip("Swap foreground/background colours (X)")
        swap_action.triggered.connect(self._on_swap_colors)
        swap_action.setShortcut("X")
        toolbar.addAction(swap_action)

        reset_colors_action = QAction("Reset Colors (D)", self)
        reset_colors_action.setToolTip("Reset to black/white (D)")
        reset_colors_action.triggered.connect(self._on_reset_colors)
        reset_colors_action.setShortcut("D")
        toolbar.addAction(reset_colors_action)

        toolbar.addSeparator()

        # --- Brush size ---
        toolbar.addWidget(QLabel("Size:"))
        self._size_spinbox = QSpinBox()
        self._size_spinbox.setMinimum(1)
        self._size_spinbox.setMaximum(8)
        self._size_spinbox.setValue(1)
        self._size_spinbox.setToolTip("Brush/line width (1-8 px)")
        self._size_spinbox.valueChanged.connect(self._on_size_changed)
        toolbar.addWidget(self._size_spinbox)

        toolbar.addSeparator()

        # --- Per-tool options (shown/hidden dynamically) ---

        # Fill tolerance
        self._tol_label = QLabel("Tol:")
        self._tol_label.setVisible(False)
        toolbar.addWidget(self._tol_label)

        self._tol_spinbox = QSpinBox()
        self._tol_spinbox.setMinimum(0)
        self._tol_spinbox.setMaximum(100)
        self._tol_spinbox.setValue(self._current_tolerance)
        self._tol_spinbox.setFixedWidth(58)
        self._tol_spinbox.setToolTip("Flood-fill colour tolerance 0-100 (0 = exact match)")
        self._tol_spinbox.valueChanged.connect(self._on_fill_tolerance_changed)
        self._tol_spinbox.setVisible(False)
        toolbar.addWidget(self._tol_spinbox)

        # Rect filled toggle
        self._filled_checkbox = QCheckBox("Filled")
        self._filled_checkbox.setChecked(self._rect_filled)
        self._filled_checkbox.setToolTip("Solid fill (unchecked = outline only)")
        self._filled_checkbox.toggled.connect(self._on_rect_filled_toggled)
        self._filled_checkbox.setVisible(False)
        toolbar.addWidget(self._filled_checkbox)

        # --- Zoom toolbar ---
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

    # ------------------------------------------------------------------
    # ICO loading
    # ------------------------------------------------------------------

    def _load_ico(self, path: Path) -> None:
        """Load an ICO file and populate the UI."""
        try:
            self._frames = read_ico(path)
            self._size_list.clear()
            for i, (_image, spec) in enumerate(self._frames):
                size_str = f"{spec.width}x{spec.height}"
                item = QListWidgetItem(size_str)
                item.setData(Qt.ItemDataRole.UserRole, i)
                font = QFont("Courier")
                item.setFont(font)
                self._size_list.addItem(item)

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

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _create_tools(self) -> None:
        """Create tool instances sharing the current canvas image."""
        if self._canvas._current_image is None:
            return
        image = self._canvas._current_image
        fg = self._palette.foreground_color
        color = (fg.red(), fg.green(), fg.blue(), fg.alpha())
        self._tools = {
            "pencil": PixelTool(image, color, self._current_size),
            "eraser": EraserTool(image, self._current_size),
            "eyedropper": EyedropperTool(image),
            "fill": FillTool(image, color, self._current_tolerance),
            "line": LineTool(image, color, self._current_size),
            "rect": RectTool(image, color, self._rect_filled),
            "select": SelectTool(image),
        }

    def _update_tool_options_visibility(self) -> None:
        """Show/hide per-tool option widgets based on active tool."""
        name = self._current_tool_name
        self._tol_label.setVisible(name == "fill")
        self._tol_spinbox.setVisible(name == "fill")
        self._filled_checkbox.setVisible(name == "rect")

    def _on_tool_pencil(self) -> None:
        """Switch to pencil tool."""
        if "pencil" not in self._tools:
            self._create_tools()
        tool = self._tools["pencil"]
        assert isinstance(tool, PixelTool)
        fg = self._palette.foreground_color
        tool.set_color((fg.red(), fg.green(), fg.blue(), fg.alpha()))
        tool.set_size(self._current_size)
        self._canvas.set_tool(tool)
        self._current_tool_name = "pencil"
        self._update_tool_options_visibility()
        self._status_bar.showMessage("Tool: Pencil (B)")

    def _on_tool_eraser(self) -> None:
        """Switch to eraser tool."""
        if "eraser" not in self._tools:
            self._create_tools()
        tool = self._tools["eraser"]
        assert isinstance(tool, EraserTool)
        tool.set_size(self._current_size)
        self._canvas.set_tool(tool)
        self._current_tool_name = "eraser"
        self._update_tool_options_visibility()
        self._status_bar.showMessage("Tool: Eraser (E)")

    def _on_tool_eyedropper(self) -> None:
        """Switch to eyedropper tool."""
        if "eyedropper" not in self._tools:
            self._create_tools()
        tool = self._tools["eyedropper"]
        self._canvas.set_tool(tool)
        self._current_tool_name = "eyedropper"
        self._update_tool_options_visibility()
        self._status_bar.showMessage("Tool: Eyedropper - click to pick colour (I)")

    def _on_tool_fill(self) -> None:
        """Switch to flood-fill tool."""
        if "fill" not in self._tools:
            self._create_tools()
        tool = self._tools["fill"]
        assert isinstance(tool, FillTool)
        fg = self._palette.foreground_color
        tool.set_color((fg.red(), fg.green(), fg.blue(), fg.alpha()))
        tool.set_tolerance(self._current_tolerance)
        self._canvas.set_tool(tool)
        self._current_tool_name = "fill"
        self._update_tool_options_visibility()
        self._status_bar.showMessage("Tool: Fill - flood fill with tolerance (G)")

    def _on_tool_line(self) -> None:
        """Switch to line tool."""
        if "line" not in self._tools:
            self._create_tools()
        tool = self._tools["line"]
        assert isinstance(tool, LineTool)
        fg = self._palette.foreground_color
        tool.set_color((fg.red(), fg.green(), fg.blue(), fg.alpha()))
        tool.set_size(self._current_size)
        self._canvas.set_tool(tool)
        self._current_tool_name = "line"
        self._update_tool_options_visibility()
        self._status_bar.showMessage("Tool: Line - click and drag (L)")

    def _on_tool_rect(self) -> None:
        """Switch to rectangle tool."""
        if "rect" not in self._tools:
            self._create_tools()
        tool = self._tools["rect"]
        assert isinstance(tool, RectTool)
        fg = self._palette.foreground_color
        tool.set_color((fg.red(), fg.green(), fg.blue(), fg.alpha()))
        tool.filled = self._rect_filled
        self._canvas.set_tool(tool)
        self._current_tool_name = "rect"
        self._update_tool_options_visibility()
        self._status_bar.showMessage("Tool: Rectangle - click and drag (R)")

    def _on_tool_select(self) -> None:
        """Switch to rectangular selection tool."""
        if "select" not in self._tools:
            self._create_tools()
        self._canvas.set_tool(self._tools["select"])
        self._current_tool_name = "select"
        self._update_tool_options_visibility()
        self._status_bar.showMessage("Tool: Select - drag to select, Ctrl+C/X/V (S)")

    # ------------------------------------------------------------------
    # Tool options
    # ------------------------------------------------------------------

    def _on_fill_tolerance_changed(self, value: int) -> None:
        """Update FillTool tolerance from spinbox."""
        self._current_tolerance = value
        tool = self._tools.get("fill")
        if isinstance(tool, FillTool):
            tool.set_tolerance(value)

    def _on_rect_filled_toggled(self, checked: bool) -> None:
        """Toggle RectTool between outline and filled mode."""
        self._rect_filled = checked
        tool = self._tools.get("rect")
        if isinstance(tool, RectTool):
            tool.filled = checked

    # ------------------------------------------------------------------
    # Clipboard (SelectTool)
    # ------------------------------------------------------------------

    def _on_copy(self) -> None:
        """Copy selected region to internal clipboard."""
        tool = self._tools.get("select")
        if not isinstance(tool, SelectTool) or tool.selection is None:
            return
        img = tool.get_selected_image()
        if img is not None:
            self._clipboard = img
            self._clipboard_origin = (tool.selection[0], tool.selection[1])
            self._status_bar.showMessage(f"Copied {img.width}x{img.height} px")

    def _on_cut(self) -> None:
        """Copy selected region to clipboard and clear selection area."""
        tool = self._tools.get("select")
        if not isinstance(tool, SelectTool) or tool.selection is None:
            return
        img = tool.get_selected_image()
        if img is None:
            return
        self._clipboard = img
        self._clipboard_origin = (tool.selection[0], tool.selection[1])
        canvas = self._canvas
        canvas._pre_stroke_image = canvas._current_image.copy()
        tool.clear_selection_area()
        canvas._refresh_pixmap()
        canvas._commit_stroke("Cut")
        self._status_bar.showMessage(f"Cut {img.width}x{img.height} px")

    def _on_paste(self) -> None:
        """Paste clipboard at original origin; sprite-aware (skips transparent pixels)."""
        if self._clipboard is None or self._canvas._current_image is None:
            return
        if "select" not in self._tools:
            self._create_tools()
        tool = self._tools.get("select")
        if not isinstance(tool, SelectTool):
            return
        canvas = self._canvas
        canvas._pre_stroke_image = canvas._current_image.copy()
        tool.paste(self._clipboard, *self._clipboard_origin)
        canvas._refresh_pixmap()
        canvas._commit_stroke("Paste")
        self._status_bar.showMessage(f"Pasted {self._clipboard.width}x{self._clipboard.height} px")

    # ------------------------------------------------------------------
    # Colour and size
    # ------------------------------------------------------------------

    def _on_color_changed(self, color: QColor, is_foreground: bool) -> None:
        """Propagate foreground colour change to all colour-bearing tools."""
        if is_foreground:
            rgba = (color.red(), color.green(), color.blue(), color.alpha())
            for key in ("pencil", "fill", "line", "rect"):
                tool = self._tools.get(key)
                if isinstance(tool, (PixelTool, FillTool, LineTool, RectTool)):
                    tool.set_color(rgba)
        self._status_bar.showMessage(
            f"{'Foreground' if is_foreground else 'Background'}: "
            f"#{color.red():02x}{color.green():02x}{color.blue():02x}"
        )

    def _on_color_sampled(self, r: int, g: int, b: int, a: int) -> None:
        """Handle colour picked by eyedropper — update palette."""
        self._palette.set_foreground_color(QColor(r, g, b, a))

    def _on_swap_colors(self) -> None:
        """Swap foreground and background colours."""
        self._palette.swap_colors()

    def _on_reset_colors(self) -> None:
        """Reset foreground/background to default black/white."""
        self._palette.reset_to_default()

    def _on_size_changed(self, value: int) -> None:
        """Update brush/line size for all size-aware tools."""
        self._current_size = value
        for key, cls in (("pencil", PixelTool), ("eraser", EraserTool), ("line", LineTool)):
            tool = self._tools.get(key)
            if isinstance(tool, cls):
                tool.set_size(value)
        self._status_bar.showMessage(f"Brush size: {value}px")

    # ------------------------------------------------------------------
    # Extract dominant colours
    # ------------------------------------------------------------------

    def _on_extract_requested(self) -> None:
        """Extract dominant colours from the current canvas image into the palette."""
        img = self._canvas.get_current_image()
        if img is None:
            return
        from icoforge.core.color_utils import extract_dominant_colors

        self._palette.set_colors(extract_dominant_colors(img))

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def _on_zoom_changed(self, zoom: float) -> None:
        """Handle zoom level change."""
        percentage = int(zoom * 100)
        self._status_bar.showMessage(f"Zoom: {percentage}%")

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

        if self._user_set_zoom and self._current_frame_index < len(self._frames):
            _, spec = self._frames[self._current_frame_index]
            self._zoom_overrides[(spec.width, spec.height)] = zoom

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
