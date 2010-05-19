#!/usr/bin/env python
# coding=utf8

import gtk
import gobject
import time

class PlayerApplet(object):
	player_markup = '<span size="50000">%s</span>'
	button_markup = '<span size="50000" font_weight="bold">%s</span>'
	time_label_markup = '<span size="80000">%s</span>'
	examination_time = 15

	def __init__(self, app, name):
		self.app = app
		self.name = name

		builder = self.app.create_builder()
		self.window = builder.get_object('player_window')
		container = builder.get_object('player_window_container')
		container.remove(self.window)
		self.app.add_to_player_container(self.window)

		# set player name
		builder.get_object('player_name').set_markup(self.player_markup % name)

		# set hotkey
		hotkey = self.app.claim_hotkey()
		builder.get_object('stop_button_label').set_markup(self.button_markup % hotkey)

		# cache object refs
		self.time_label = builder.get_object('time_label')

		self.app.register_player(self)

		builder.connect_signals(self)

		self.reset()

		self.window.show()

	def show_time_diff(self, delta):
		time_str = "%02d:%02d.%03d" % (delta/60, delta%60, (delta%1)*1000)
		self.time_label.set_markup(self.time_label_markup % time_str)

	def calc_time(self, current_time):
		return current_time - self.start_time - self.examination_time

	@property
	def running(self):
		return None != self.start_time and None == self.stop_time

	@property
	def stopped(self):
		return None != self.stop_time

	def in_examination(self, current_time):
		return self.calc_time(current_time) < self.examination_time

	def start(self, start_time = None):
		if not start_time:
			start_time = time.time()
		self.start_time = start_time

	def reset(self):
		self.start_time = None
		self.stop_time = None
		time_str = "%d" % self.examination_time
		self.time_label.set_markup(self.time_label_markup % time_str)

	def stop(self, stop_time = None):
		if not stop_time:
			stop_time = time.time()
		self.stop_time = stop_time

		self.show_time_diff(self.calc_time(self.stop_time))

	def update(self, current_time = None):
		if not self.running:
			return
		else:
			time_elapsed = current_time - self.start_time
			if self.examination_time > time_elapsed:
				time_str = "%d" % (self.examination_time-time_elapsed)
				self.time_label.set_markup(self.time_label_markup % time_str)
			else:
				self.show_time_diff(self.calc_time(current_time))

	def on_player_toggle_activate(self, *args):
		if self.running:
			if self.in_examination(time.time()):
				self.reset()
			else:
				self.stop()
		elif self.stopped:
			self.reset()
		else:
			self.start()


class RubikApp(object):
	def __init__(self, ui_file = 'ui.glade'):
		self.ui_file = ui_file

		# init main window
		self.builder = self.create_builder()

		self.main_window = self.builder.get_object('main_window')
		self.player_container = self.builder.get_object('player_container')
		self.player_container_maxcols = 4
		self.num_players = 0
		self.main_window.show()

		self.hotkeys_available = ['q','e','r','y','i','p']
		self.players = []

		self.builder.connect_signals(self)

		gobject.timeout_add(10, self.tick)

	def tick(self):
		current_time = time.time()
		for player in self.players:
			player.update(current_time)
		return True

	def create_builder(self):
		builder = gtk.Builder()
		builder.add_from_file(self.ui_file)

		return builder

	def gtk_main_quit(self, *args):
		gtk.main_quit()

	def player_container_inc(self):
		pos = (self.num_players % self.player_container_maxcols, self.num_players / self.player_container_maxcols)
		self.num_players += 1

		self.player_container.resize(
			min(self.num_players, self.player_container_maxcols),
			self.num_players / self.player_container_maxcols + 1
		)

		return pos

	def add_to_player_container(self, window):
		(x, y) = self.player_container_inc()
		self.player_container.attach(window, x, x+1, y, y+1)

	def claim_hotkey(self):
		return self.hotkeys_available.pop(0)

	def register_player(self, player):
		self.players.append(player)

	def on_start_action_activate(self, *args):
		print "START"

	def on_reset_action_activate(self, *args):
		print "RESET"

	def on_add_player_action_activate(self, *args):
		print "NEW PLAYER"
		builder = self.create_builder()
		dialog = builder.get_object('new_player_dialog')
		player_name_entry = builder.get_object('player_name_entry')
		player_name_entry.connect("activate", lambda x: dialog.response(0))

		while True:
			response = dialog.run()
			if 1 == response:
				name = False
				break
			name = player_name_entry.get_text().strip()
			if "" == name: continue
			break
		dialog.destroy()

		if name:
			# now add a new player named "name"
			PlayerApplet(self, name)

	def on_clear_action_activate(self, *args):
		print "CLEAR"

if '__main__' == __name__:
	app = RubikApp()
	gtk.main()
