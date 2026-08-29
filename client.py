#!/usr/bin/python3

# Harbard - Solanum IRCd management bot
# Sends REHASH SSLD on OpenSSL package upgrades
#
# Requires corresponding syslog bot to post messages to log channel
# when the upgrade occurs, and a post-installation script for the
# OpenSSL package to trigger the syslog message
#
# Copyright (C) 2025 Aaron M. D. Jones <aaron@alphachat.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import argparse
import asyncio
import re
import sys

from AlphaChat.ConfigPydle import ConfigPydleClient



class HarbardClient(ConfigPydleClient):

	def __init__(self, *args, **kwargs):

		super().__init__(*args, **kwargs)

		self.my_server_name = None

		try:
			pattern = re.compile(self.acconfig['upgrade_pattern'])
			groupid = pattern.groupindex['hostname']
			self.upgrade_pattern = pattern
		except KeyError as e:
			raise ValueError(f'Configuration item "upgrade_pattern" regular expression ' \
			                 f'lacks the required match group "{str(e)}"')
		except Exception as e:
			raise ValueError(f'Configuration item "upgrade_pattern" regular expression ' \
			                 f'could not be compiled: {type(e)}: {str(e)}')

		if '{server_name}' not in self.acconfig['remote_rehash_command']:
			raise ValueError('Configuration item "remote_rehash_command" requires a ' \
			                 '"{server_name}" format parameter')

		if not isinstance(self.acconfig['server_name_map'], dict):
			raise ValueError('Configuration item "server_name_map" must be a dictionary')

		self.acchannels.add(self.acconfig['log_channel'])



	async def log_message(self, message):

		message = f'\x03{self.acconfig["message_colour"]:02}{message}\x03'

		await self.message(self.acconfig['log_channel'], message)



	async def on_raw_004(self, message):

		await super().on_raw_004(message)

		self.my_server_name = message.params[1]



	async def on_channel_message(self, target, source, message):

		await super().on_channel_message(target, source, message)

		if not self.is_same_channel(target, self.acconfig['log_channel']):
			return await self.part(target)

		match = self.upgrade_pattern.fullmatch(message)
		if not match:
			return

		if self.my_server_name is None:
			return await self.quit('I could not determine my IRCd server name')

		hostname = match.group('hostname')

		if hostname not in self.acconfig['server_name_map']:
			return

		if self.acconfig['server_name_map'][hostname]:
			server_name = self.acconfig['server_name_map'][hostname]
		else:
			server_name = hostname

		server_names = server_name.split()

		for server_name in server_names:

			if server_name == self.my_server_name:
				command = self.acconfig['local_rehash_command']
			else:
				command = self.acconfig['remote_rehash_command']

			if '{server_name}' in command:
				command = command.format(server_name=server_name)

			await self.log_message(f'Executing "{command}" ...')
			await self.raw(f'{command}\r\n')



if __name__ == '__main__':

	default_config_keys = {
		'message_colour':       13,
	}

	required_config_keys = [
		'local_rehash_command',
		'log_channel',
		'remote_rehash_command',
		'server_name_map',
		'upgrade_pattern',
	]

	parser = argparse.ArgumentParser()
	parser.add_argument('--config', default='client.yaml')
	args = parser.parse_args()

	client = HarbardClient(args.config, default_config_keys, required_config_keys)
	client.run()
	sys.exit(1)
