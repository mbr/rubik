#!/usr/bin/env python
# coding=utf8

import gtk
import gobject
import time
import math

from xml.sax.saxutils import escape as xml_escape

class PlayerApplet(object):
	player_markup = '<span size="50000">%s</span>'
	button_markup = '<span size="50000" font_weight="bold">%s</span>'
	time_label_markup = '<span size="80000">%s</span>'

	def __init__(self, app, name, hotkey):
		self.app = app
		self.name = name
		self.hotkey = hotkey

		print "MY HOTKEY",hotkey

		# configuration values
		self.examination_time = self.app.conf['examination_time']

		# remove window from container
		builder = self.app.create_builder()
		self.window = builder.get_object('player_window')
		container = builder.get_object('player_window_container')
		container.remove(self.window)

		# set player name
		builder.get_object('player_name').set_markup(self.player_markup % xml_escape(name))

		# attach
		self.app.attach(self)
		builder.get_object('stop_button_label').set_markup(self.button_markup % xml_escape(gtk.accelerator_name(*self.hotkey)))

		# cache object refs
		self.time_label = builder.get_object('time_label')

		self.reset()

		builder.connect_signals(self)
		self.window.show()


	def calc_time(self, end_time = None):
		if not end_time:
			end_time = self.app.get_time()
		return end_time - self.start_time - self.examination_time

	@property
	def running(self):
		return None != self.start_time and None == self.stop_time

	@property
	def stopped(self):
		return None != self.stop_time

	@property
	def in_examination(self):
		return self.calc_time() < 0

	def start(self):
		self.reset()
		self.start_time = self.app.get_time()
		self.redraw()

	def reset(self):
		self.start_time = None
		self.stop_time = None
		self.redraw()

	def stop(self):
		self.stop_time = self.app.get_time()
		self.redraw()

	def redraw(self):
		delta = False
		time_str = "Ready"
		if self.running:
			if self.in_examination:
				time_str = "%d" % math.ceil(abs(self.calc_time()))
			else:
				delta = self.calc_time()
		elif self.stopped:
			delta = self.calc_time(self.stop_time)

		if delta:
			time_str = "%02d:%02d.%02d" % (delta/60, delta%60, (delta%1)*100)
		self.time_label.set_markup(self.time_label_markup % xml_escape(time_str))


	def update(self, current_time = None):
		if not self.running:
			return
		else:
			self.redraw()

	def on_player_toggle_activate(self, *args):
		if self.running:
			if self.in_examination:
				self.reset()
			else:
				self.stop()
		elif self.stopped:
			self.reset()
		else:
			self.start()


class NewPlayerDialog(object):
	def __init__(self, app):
		builder = app.create_builder()
		self.app = app
		self.dialog = builder.get_object('new_player_dialog')
		self.player_name_entry = builder.get_object('player_name_entry')
		self.player_name_entry.connect("activate", lambda x: self.dialog.response(0))

		self.hotkey_togglebutton = builder.get_object('hotkey_togglebutton')
		self.hotkey = None
		self.set_capturing(False)

		builder.connect_signals(self)

	def set_capturing(self, capturing):
		print "NOW:",capturing
		self.capturing = capturing

		label = self.hotkey_togglebutton.get_child()

		if capturing:
			label.set_text('Press your desired hotkey nows')
			self.hotkey_togglebutton.set_active(True)
		else:
			if self.hotkey:
				label.set_text(gtk.accelerator_name(*self.hotkey))
			else:
				label.set_text('Press to set hotkey')
				self.hotkey_togglebutton.set_active(False)

	def run(self):
		rv = False
		while True:
			response = self.dialog.run()
			if 1 == response:
				break
			self.name = self.player_name_entry.get_text().strip()
			if not self.name:
				error_dlg = gtk.MessageDialog(self.dialog, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "Please enter a name")
				error_dlg.run()
				error_dlg.destroy()
			elif not self.hotkey:
				error_dlg = gtk.MessageDialog(self.dialog, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "Please select a hotkey by clicking the hotkey button and pressing a key.")
				error_dlg.run()
				error_dlg.destroy()
			else:
				rv = True
				break
		self.dialog.destroy()

		return rv

	def on_hotkey_togglebutton_toggled(self, *args):
		self.set_capturing(self.hotkey_togglebutton.get_active())

	def on_new_player_dialog_key_press_event(self, dialog, event):
		if self.capturing:
			#hotkey = (event.keyval, event.state)
			hotkey = (event.keyval, 0)
			if self.app.hotkey_available(hotkey): self.hotkey = hotkey
			else:
				error_dlg = gtk.MessageDialog(self.dialog, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, "That hotkey is already taken.")
				error_dlg.run()
				error_dlg.destroy()
			self.hotkey_togglebutton.set_active(False)
			return True


class RubikApp(object):
	def __init__(self, ui_file = 'ui.glade'):
		self.ui_file = ui_file
		self.conf = {
			'examination_time': 2,
			'player_container_maxcols': 4,
		}

		# init main window
		self.builder = self.create_builder()

		self.main_window = self.builder.get_object('main_window')
		self.player_container = self.builder.get_object('player_container')
		self.main_window.show()

		# init hotkeys and players
		self.players = []
		self.used_hotkeys = []

		# set up keyboard shortcuts
		self.accel_group = gtk.AccelGroup()
		(key, mod) = gtk.accelerator_parse("F2")
		self.used_hotkeys.append( (key,mod) )
		self.accel_group.connect_group(key, mod, 0, self.on_start_action_activate)
		(key, mod) = gtk.accelerator_parse("F5")
		self.used_hotkeys.append( (key,mod) )
		self.accel_group.connect_group(key, mod, 0, self.on_reset_action_activate)
		(key, mod) = gtk.accelerator_parse("F10")
		self.used_hotkeys.append( (key,mod) )
		self.accel_group.connect_group(key, mod, 0, self.on_add_player_action_activate)
		(key, mod) = gtk.accelerator_parse("<Control>F10")
		self.used_hotkeys.append( (key,mod) )
		self.accel_group.connect_group(key, mod, 0, self.on_clear_action_activate)
		self.main_window.add_accel_group(self.accel_group)

		self.builder.connect_signals(self)

		self.tick()
		gobject.timeout_add(10, self.tick)

	@property
	def num_players(self):
		return len(self.players)

	def new_hotkey(self, hotkey, callback):
		(key, mod) = hotkey
		self.accel_group.connect_group(key, mod, 0, callback)
		self.used_hotkeys.append(hotkey)

	def reclaim_hotkey(self, hotkey):
		(key, mod) = hotkey
		self.accel_group.disconnect_key(key, mod)
		self.used_hotkeys.remove(hotkey)

	def hotkey_available(self, hotkey):
		return hotkey not in self.used_hotkeys

	def get_time(self):
		return self.current_time

	def tick(self):
		self.current_time = time.time()
		for player in self.players:
			player.update()
		return True

	def create_builder(self):
		builder = gtk.Builder()
		builder.add_from_file(self.ui_file)

		return builder

	def gtk_main_quit(self, *args):
		gtk.main_quit()

	def attach(self, player):
		maxcols = self.conf['player_container_maxcols']
		(x, y) = (self.num_players % maxcols, self.num_players / maxcols)
		self.players.append(player)

		self.player_container.attach(player.window, x, x+1, y, y+1)
		self.player_container.resize(max(maxcols, self.num_players%4), self.num_players/4 + 1)
		self.new_hotkey(player.hotkey, player.on_player_toggle_activate)

	def unattach(self, player):
		self.players.remove(player)
		self.player_container.remove(player.window)

		self.reclaim_hotkey(player.hotkey)

	def on_start_action_activate(self, *args):
		self.current_time = time.time()
		for player in self.players:
			player.start()

	def on_reset_action_activate(self, *args):
		for player in self.players:
			player.reset()

	def on_add_player_action_activate(self, *args):
		builder = self.create_builder()
		dialog = NewPlayerDialog(self)

		if dialog.run():
			PlayerApplet(self, dialog.name, dialog.hotkey)

	def on_clear_action_activate(self, *args):
		for player in list(self.players):
			self.unattach(player)

if '__main__' == __name__:
	app = RubikApp()
	gtk.main()
