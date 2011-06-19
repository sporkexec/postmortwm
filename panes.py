#
# panes.py -- Handle panes (sometimes known as "frames")
#
#	Copyright (C) 2001  Mike Meyer <mwm@mired.org>
#	Copyright (C) 2011  Jacob Courtneay <jacob@sporkexec.com>
#
#	This program is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; either version 2 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Panes - provide panes to put plwm windows in.

The idea is that each screen is completely covered by panes. Each
pixel on the screen must belong to one and only one pane. Focus
ignores the mouse, but is moved from pane to pane via the
keyboard. Windows open in the current pane, and are told to resize
themselves to fit that pane.

The rest of the UI - well, that's up to you."""

from Xlib import X, Xutil, Xatom
from plwm import wmanager, wmevents, modewindow, cfilter
try:
	from functools import partial # Python >= 2.5
except ImportError, e:
	def partial(fun, **kwargs):
		def wrapper(*args_called, **kwargs_called):
			kw = dict(kwargs)
			kw.update(kwargs_called)
			return fun(*args_called, **kw)
		return wrapper


WM_TRANSIENT_FOR = None
class panesScreen:
	"paneScreen - pane mixin for Screens."

	panes_window_gravity = X.CenterGravity
	panes_maxsize_gravity = X.CenterGravity
	panes_transient_gravity = X.CenterGravity

	def __screen_client_init__(self):
		"Create the initial pane object for this screen."
		global WM_TRANSIENT_FOR
		# Warning - if we manage more than one display, this breaks!
		if not WM_TRANSIENT_FOR:
			WM_TRANSIENT_FOR = self.wm.display.intern_atom("WM_TRANSIENT_FOR")

		self.panes_list = []
		self.current_pane = None

		wmanager.debug('panesScreen', 'Initializing screen %d', self.number)
		self.dispatch.add_handler(X.ConfigureRequest, self.panes_configure)
		pane = Pane(self, 0, 0, self.root_width, self.root_height)
		self.panes_fullscreen(pane)
		self.panes_add(pane)

	def panes_fullscreen(self, pane):
		"Make the pane use the all the available screen."

		pane.width = self.root_width
		pane.x = 0
		pane.height = self.root_height
		pane.y = 0

	def panes_configure(self, event):
		"A window changed, so pass it on to my pane."

		w = self.get_window(event.window)
		if w and w.pane:
			if event.value_mask & (X.CWX | X.CWY | X.CWWidth | X.CWHeight):
				w.pane.place_window(w)
			if event.value_mask & X.CWStackMode and event.stack_mode == X.Above \
				and self.allow_self_changes(w):
				w.pane.add_window(w)

	#####
	def panes_add(self, pane):
		"Add the given pane to the list of all panes."

		wmanager.debug('panesManager', 'added pane %s', `pane`)
		self.panes_list.append(pane)
		if self.current_pane is None: self.current_pane = self.panes_list[0]

	def panes_remove(self, test):
		"Remove panes that match the filter."

		old = self.current_pane
		self.panes_list = filter(cfilter.Not(test), self.panes_list)
		try: self.panes_list.index(old)
		except ValueError: self.current_pane = self.panes_list[0]


class panesClient:
	"""panesClient - pane mixin for clients

	Note that this needs to be mixed in *after* any mixins that affect window
	geometry, such as border."""

	def __client_init__(self):
		"Arrange to open in the current pane."

		wmanager.debug('Pane', 'Initing client %s', self)
		# Set this clients gravity
		if self.window.get_property(WM_TRANSIENT_FOR, Xatom.WINDOW, 0, 1) is not None:
			self.panes_gravity = self.screen.panes_transient_gravity
		elif self.sizehints and self.sizehints.flags & Xutil.PMaxSize:
			self.panes_gravity = self.screen.panes_maxsize_gravity
		else:
			self.panes_gravity = self.screen.panes_window_gravity

		self.pane = None
		pane = self.screen.current_pane
		if pane.screen != self.screen:
			pane = filter(lambda p, m=self.screen: p.screen == m, self.screen.panes_list)[0]
		pane.add_window(self)
		self.dispatch.add_handler(X.UnmapNotify, self.panes_unmap)
		self.dispatch.add_handler(X.DestroyNotify, self.panes_unmap)

	def panes_unmap(self, event):
		"The window is going away or gone - make sure it's not taking up a pane"

		if self.pane: self.pane.remove_window(self)


class Pane:
	"Pane - the object(s) that manages windows on the screen."

	def __init__(self, screen, x, y, width, height):
		"Initialize a pane of the given size on the given screen."

		self.screen, self.x, self.y, self.width, self.height = screen, x, y, width, height
		self.wm = screen.wm
		self.window = None
		self.window_list = []

	def add_window(self, window):
		"Add a window to this pane."

		if window in self.window_list:
			return
		wmanager.debug('Pane', 'Adding window %s to pane %s', window, self)

		self.window_list.append(window)
		prev_pane = window.pane
		if prev_pane != self:
			if prev_pane:
				prev_pane.remove_window(window)
			self.place_window(window)
			window.pane = self
		self.window = window
		self.activate()

	def remove_window(self, window):
		"Disown a window and cycle a new one into focus."

		if window.pane != self or window not in self.window_list:
			return
		wmanager.debug('Pane', 'Removing window %s from pane %s' % (window, self))
		window.pane = None
		windex = self.window_list.index(window)
		self.window_list.remove(window)
		if self.window == window:
			# Jump back towards the beginning of the window list.
			if windex > 0:
				windex -= 1
			elif self.window_list != []:
				windex = 0
			else:
				self.window = None
				if self.screen.current_pane == self:
					self.wm.set_current_client(None)
				return

			self.window = self.window_list[windex]
			if self.screen.current_pane == self:
				self.activate()

	def place_window(self, window = None):
		"Figure out where the window should be put."

		if window is None:
			window = self.window
		if window is None:
			return
		wmanager.debug('Pane', 'Placing window %s for pane %s' % (window, self))

		# Bypassing size hints/gravity, they seem useless for tiles.
		width = self.width - 2 * window.border_width
		height = self.height - 2 * window.border_width
		x, y = self.x, self.y
		x, y, width, height = window.keep_on_screen(x, y, width, height)

		wmanager.debug('Pane-configure', 'Resizing window from %d, %d to %d, %d' %
						(window.width, window.height, width, height))
		window.moveresize(x, y, width, height)

	def force_window(self):
		"Try and force an application to notice what size it's window is."

		if not self.window:
			return
		self.window.resize(self.width / 2, self.height / 2)
		self.wm.display.flush()
		self.place_window()

	def deactivate(self):
		"A place to do anything appropriate for us when losing the focus."

		if self.window and not self.window.withdrawn:
			if self.screen.current_pane == self:
				self.wm.set_current_client(None)
		event = paneBlur()
		event.pane = self
		self.wm.misc_dispatch.dispatch_event(event)

	def activate(self):
		"Activate whatever is currently my window."

		self.wm.current_screen = self.screen
		if self.screen.current_pane != self:
			self.screen.current_pane.deactivate()
			self.screen.current_pane = self
		if self.window and not self.window.withdrawn:
			wmanager.debug('Pane', 'Activating window %s in pane %s' %
							(self.window, self))
			self.window.activate()
			self.window.warppointer()
		event = paneFocus()
		event.pane = self
		self.wm.misc_dispatch.dispatch_event(event)

	def horizontal_split(self, frac = .5):
		"Split the pane horizontally, taking frac off the bottom."

		if not 0 < frac < 1:
			raise ValueError, "Pane splits must be between 0 and 1."

		new_height = int(self.height * frac)
		self.height = self.height - new_height
		new_y = self.y + self.height
		map(self.place_window, self.screen.query_clients(panefilter(self)))
		new_pane = Pane(self.screen, self.x, new_y, self.width, new_height)
		self.screen.panes_add(new_pane)
		new_pane.activate()

	def vertical_split(self, frac = .5):
		"Split the pane vertically, taking frac off the right."

		if not 0 < frac < 1:
			raise ValueError, "Pane splits must be between 0 and 1."

		new_width = int(self.width * frac)
		self.width = self.width - new_width
		new_x = self.x + self.width
		map(self.place_window, self.screen.query_clients(panefilter(self)))
		new_pane = Pane(self.screen, new_x, self.y, new_width, self.height)
		self.screen.panes_add(new_pane)
		new_pane.activate()

	def maximize(self):
		"Make me the only pane on my screen."

		self.screen.panes_remove(lambda x, s = self.screen, m = self:
							x.screen == s and x != m)
		self.screen.panes_fullscreen(self)
		for window in self.screen.query_clients():
			window.pane = self
			self.place_window(window)
		self.activate()

	def switch_window(self, index):
		"Raise and focus a particular window owned by this pane."
		if not 0 <= index < len(self.window_list):
			return
		if self.window and self.window_list.index(self.window) == index:
			return
		self.window = self.window_list[index]
		self.activate()

	__diff_filters = {
		# Filters to select panes in the correct general direction.
		# Chosen panes will tend to be towards upper left corner when
		# panes are staggered.
		# inputs: from_edges, to_edges
		# returns filtering bool

		# dest must be below and not to the right of current
		'down': lambda (tt, rr, bb, ll), (t, r, b, l): bb <= t and l <= ll,
		# dest must be above and not to the right of current
		'up': lambda (tt, rr, bb, ll), (t, r, b, l): b <= tt and l <= ll,
		# dest must be to the right of and not below current
		'right': lambda (tt, rr, bb, ll), (t, r, b, l): rr <= l and t <= tt,
		# dest must be to the left of and not below current
		'left': lambda (tt, rr, bb, ll), (t, r, b, l): r <= ll and t <= tt,
	}
	__diff_orders = {
		# Once filtered by direction, chooses the closest pane according to
		# upper left corner coordinates.
		# inputs: from_edges, to_edges
		# returns two numbers to be used as sorting keys, sort of like:
		# ORDER BY ret[0] ASC, ret[1] ASC LIMIT 1

		# vdiff, hdiff
		'down': lambda (tt, rr, bb, ll), (t, r, b, l): (abs(tt - t), abs(ll - l)),
		'up': lambda (tt, rr, bb, ll), (t, r, b, l): (abs(tt - t), abs(ll - l)),
		# hdiff, vdiff
		'right': lambda (tt, rr, bb, ll), (t, r, b, l): (abs(ll - l), abs(tt - t)),
		'left': lambda (tt, rr, bb, ll), (t, r, b, l): (abs(ll - l), abs(tt - t)),
	}

	def get_edges(self):
		"""Return the edges of the pane as (top, right, bottom, left)"""
		return (self.y, self.x + self.width,
			self.y + self.height, self.x)

	def get_neighbor(self, dir):
		"""Find the closest pane in the specified direction.

		dir is either 'up', 'down', 'left' or 'right'.
		We assume a perfectly tiled layout because it's a tiled wm...
		You may get stuck if there are holes between tiles.
		We currently do not wrap around the screen."""

		edges = self.get_edges()
		dfilter = partial(self.__diff_filters[dir], edges)
		dsort = partial(self.__diff_orders[dir], edges)

		best = None
		bestdiff = None

		for p in self.screen.panes_list:
			p_edges = p.get_edges()
			if p is self or not dfilter(p_edges):
				continue

			p_diff = dsort(p_edges)
			if (bestdiff is None or p_diff[0] < bestdiff[0] or
					(p_diff[0] == bestdiff[0] and p_diff[1] < bestdiff[1])):
				best = p
				bestdiff = p_diff
		return best

	def move_window(self, dir):
		"""Give the current window to another pane."""
		neighbor = self.get_neighbor(dir)
		if neighbor is None or self.window is None:
			self.wm.move_focus(dir)
			return
		neighbor.add_window(self.window)

class panefilter:
	"Filter for windows mapped in the current pane."
	def __init__(self, pane):
		"Set the pane we're active in."
		self.pane = pane
	def __call__(self, window):
		"Check to see if this is our pane."
		return self.pane == window.pane

class paneFocus:
	pane = None
class paneBlur:
	pane = None


# TODO MAYBE: Outlines are actually drawn within the pane, ie obscuring windows. Is this bad?
class OutlinePane:
	"""Draws a border around (within, rather) a pane.

	We use four small windows to draw the edges of the border. Reparenting or
	using normal border won't work because we won't always have a window to
	draw around; we only deal with panes.
	"""
	border_width = 1
	group = 'Pane'

	def __init__(self, wm):
		handlers = (
			(self.outline_show, lambda e: isinstance(e, paneFocus), self.group),
			(self.outline_hide, lambda e: isinstance(e, paneBlur), self.group),
		)
		for h in handlers:
			wm.misc_dispatch.add_handler(*h)

	def outline_show(self, event):
		self.outline_hide(event)
		pane = event.pane
		pane.outline_windows = []

		# Grab 4 windows with no border, white background.
		# TODO: Figure out how to do more colors.
		for _ in range(4):
			pane.outline_windows.append(pane.screen.root.create_window(
				0, 0, 1, 1, 0, X.CopyFromParent,
				background_pixel = pane.screen.info.white_pixel,
				save_under = 1
				))

		bw = self.border_width
		edges = pane.get_edges()
		width = edges[1] - edges[3]
		height = edges[2] - edges[0]

		# Resize windows.
		pane.outline_windows[0].configure(x = edges[3], y = edges[0], width = width, height = bw) #t
		pane.outline_windows[1].configure(x = edges[1] - bw, y = edges[0], width = bw, height = height) #r
		pane.outline_windows[2].configure(x = edges[3], y = edges[2] - bw, width = width, height = bw) #b
		pane.outline_windows[3].configure(x = edges[3], y = edges[0], width = bw, height = height) #l

		for w in pane.outline_windows:
			w.configure(stack_mode = X.Above)
			w.map()

	def outline_hide(self, event):
		pane = event.pane
		if not hasattr(pane, 'outline_windows') or pane.outline_windows is None:
			return
		for w in pane.outline_windows:
			w.destroy()
		pane.outline_windows = None

