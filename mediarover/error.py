# Copyright 2009 Kieran Elliott <kierse@mediarover.tv>
#
# Media Rover is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Media Rover is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

class CleanupError(Exception): pass
class ConfigurationError(Exception): pass
class FailedDownload(Exception): pass
class FilesystemError(Exception): pass
class InvalidArgument(Exception): pass
class InvalidData(Exception): pass
class InvalidEpisodeString(Exception): pass
class InvalidItemTitle(Exception): pass
class InvalidJobTitle(Exception): pass
class InvalidMultiEpisodeData(Exception): pass
class InvalidRemoteData(Exception): pass
class InvalidURL(Exception): pass
class MissingParameterError(Exception): pass
class QueueDeletionError(Exception): pass
class QueueInsertionError(Exception): pass
class QueueRetrievalError(Exception): pass
class SchemaMigrationError(Exception): pass
class TooManyParametersError(Exception): pass
class UnexpectedArgumentCount(Exception): pass
class UnknownQueue(Exception): pass
class UnsupportedCategory(Exception): pass
class UrlRetrievalError(Exception): pass

