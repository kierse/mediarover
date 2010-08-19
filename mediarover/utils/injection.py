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

# dependency injection solution based on recipe found at:
# http://code.activestate.com/recipes/413268/

# variables- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

broker = None

# public methods - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def no_assertion(obj): 
	return True

def is_instance_of(*classes):
   def test(obj): return isinstance(obj, classes)
   return test

def has_attributes(*attributes):
   def test(obj):
      for each in attributes:
         if not hasattr(obj, each): return False
      return True
   return test

def has_methods(*methods):
   def test(obj):
      for each in methods:
         try:
            attr = getattr(obj, each)
         except AttributeError:
            return False
         if not callable(attr): return False
      return True
   return test

def initialize_broker():
	global broker
	if broker is None:
		broker = DependencyBroker()
	return broker

# class definitions- - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class DependencyBroker(object):

	def register(self, feature, provider, *args, **kwargs):
		if not self.allowReplace:
			assert not self.providers.has_key(feature), "Duplicate feature: %r" % feature

		if callable(provider):
			def call(): return provider(*args, **kwargs)
		else:
			def call(): return provider

		self.providers[feature] = call

	def __getitem__(self, feature):
		try:
			provider = self.providers[feature]
		except KeyError:
			raise KeyError, "Unknown feature named '%s'" % feature
		return provider()

	def __contains__(self, key):
		if key in self.providers:
			return True
		return False

	def __init__(self, allowReplace=True):
		self.providers = {}
		self.allowReplace = allowReplace

class Dependency(object):

   def __get__(self, *args):
      return self.result 

   def __getattr__(self, name):
      assert name == 'result', "Unexpected attribute request other then 'result'"
      self.result = self.request()
      return self.result

   def request(self):
		obj = broker[self.feature]
		assert self.assertion(obj), \
			"The value %r of %r does not match the specified criteria" \
			% (obj, self.feature)
		return obj

   def __init__(self, feature, assertion=no_assertion):
      self.feature = feature
      self.assertion = assertion

