# resize.py: functions to help resize panes.
# Almost directly ported from ratpoison's resizing code because this stuff is hard.

from panes import panefilter

def resize_pane(frame, action, diff=10):
	if action == 'vgrow':
		resize_frame_vertically(frame, diff)
	elif action == 'vshrink':
		resize_frame_vertically(frame, -diff)
	elif action == 'hgrow':
		resize_frame_horizontally(frame, diff)
	elif action == 'hshrink':
		resize_frame_horizontally(frame, -diff)

# Save pane layout of a screen.
def screen_copy_frameset(s):
	return [p.get_edges() for p in s.panes_list]
def screen_restore_frameset(screen, frames):
	for pane, (t,r,b,l) in zip(screen.panes_list, frames):
		pane.x = l
		pane.y = t
		pane.width = r - l
		pane.height = b - t
		pane.replace_all()

frame_top = lambda f: f.y
frame_right = lambda f: f.x + f.width
frame_bottom = lambda f: f.y + f.height
frame_left = lambda f: f.x

def frame_resize_left(frame, amount):
	frame.x -= amount
	frame.width += amount
def frame_resize_right(frame, amount):
	frame.width += amount
def frame_resize_up(frame, amount):
	frame.y -= amount
	frame.height += amount
def frame_resize_down(frame, amount):
	frame.height += amount

def resize_frame_right (frame, pusher, diff):
	return resize_frame (frame, pusher, diff,
		frame_left, frame_top, frame_right, frame_bottom,
		frame_resize_right, frame_resize_left, resize_frame_left)
def resize_frame_left (frame, pusher, diff):
	return resize_frame (frame, pusher, diff,
		frame_right, frame_top, frame_left, frame_bottom,
		frame_resize_left, frame_resize_right, resize_frame_right)
def resize_frame_top (frame, pusher, diff):
	return resize_frame (frame, pusher, diff,
		frame_bottom, frame_left, frame_top, frame_right,
		frame_resize_up, frame_resize_down, resize_frame_bottom)
def resize_frame_bottom (frame, pusher, diff):
	return resize_frame (frame, pusher, diff,
		frame_top, frame_left, frame_bottom, frame_right,
		frame_resize_down, frame_resize_up, resize_frame_top)


''' Resize frame diff pixels by expanding it to the right. If the frame
   is against the right side of the screen, expand it to the left. '''
def resize_frame_horizontally(frame, diff):
	s = frame.screen
	if len(s.panes_list) < 2 or diff == 0:
		return
	if frame.width + diff <= 0:
		return
	edges = frame.get_edges() # trbl

	# Find out which resize function to use.
	if edges[1] < s.root_width:
		resize_fn = resize_frame_right
	elif edges[3] > 0:
		resize_fn = resize_frame_left
	else:
		return

	# Copy the frameset. If the resize fails, then we restore the original one.
	l = screen_copy_frameset (s)
	if resize_fn(frame, None, diff) == -1:
		screen_restore_frameset (s, l)

''' Resize frame diff pixels by expanding it down. If the frame is
   against the bottom of the screen, expand it up. '''
def resize_frame_vertically (frame, diff):
	s = frame.screen
	if len(s.panes_list) < 2 or diff == 0:
		return
	if frame.height + diff <= 0:
		return
	edges = frame.get_edges() # trbl

	# Find out which resize function to use.
	if edges[2] < s.root_height:
		resize_fn = resize_frame_bottom
	elif edges[0] > 0:
		resize_fn = resize_frame_top
	else:
		return

	# Copy the frameset. If the resize fails, then we restore the original one.
	l = screen_copy_frameset (s)
	if resize_fn(frame, None, diff) == -1:
		screen_restore_frameset (s, l)



def resize_frame (frame, pusher, diff, c1, c2, c3, c4,
					resize1, resize2, resize3):
	s = frame.screen

	# Loop through the frames and determine which ones are affected by resizing frame. 
	for cur in s.panes_list:
		if cur == frame or cur == pusher:
			continue
		# If cur is touching frame along the axis that is being
		#	 moved then this frame is affected by the resize. 
		if c1(cur) == c3(frame):
			# If the frame can't get any smaller, then fail. 
			if diff > 0 and abs(c3(cur) - c1(cur)) - diff <= 0:
				return -1
			if c2(cur) >= c2(frame) and c4(cur) <= c4(frame):
				''' Test for this circumstance:
				--+
				| |+-+
				|f||c|
				| |+-+
				--+

				In this case, resizing cur will not affect any other
				frames, so just do the resize.
				'''
				resize2(cur, -diff)
				cur.replace_all()
			elif ((c2(cur) < c2(frame) and c4(cur) > c4(frame))
					or (c2(cur) >= c2(frame) and c2(cur) < c4(frame))
					or (c4(cur) > c2(frame) and c4(cur) <= c4(frame))):
				''' Otherwise, cur's corners are either strictly outside
				frame's corners, or one of them is inside and the other
				isn't. In either of these cases, resizing cur will affect
				other adjacent frames, so find them and resize them first
				(recursive step) and then resize cur. '''
				# Attempt to resize cur. 
				if resize3(cur, frame, -diff) == -1:
					return -1

	# Finally, resize the frame and the windows inside. 
	resize1(frame, diff)
	frame.replace_all()
	frame.activate()
	return 0
