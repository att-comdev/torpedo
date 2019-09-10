Expanding the Torpedo framework
===============================

Adding new testcases to Torpedo Orchestrator
--------------------------------------------

Create the new testcase:
------------------------

Create file <testcase>.py inplugins/orchestrator/torpedo_orchestrator
directory with the following structure

::
	from base import Base

	class <classname>(Base):

		def get(self):
			<your logic goes here>

		def post(self)
			<your logic goes here>

**Note**: In case if a new Openstack/UCP/Kubernetes testcase is added, In
addition to Base class Openstack/UCP/Kubernetes class should also be imported.

Build the api JSON
------------------

Add the api json of the testcase to the existing api json at
testcases.json

::
	{
		testcase: {
			"name": <name of the testcase>
			"service-mapping": <the class name of the testcase to execute>
			"service_type": <Service type as mentioned in Keystone>
			"operation": <GET or POST operation>
			"url": <the url /servers in case of nova, /stacks in case of Heat>
			"repeat": "repeat" (Number of times a test case needs to be
				executed. Would be replaced dynamically upon executing testcase)
			"duration": "duration" ks in case of Heat>
			"repeat": "repeat" (Duration for which a test case needs to be
				executed. Would be replaced dynamically upon executing testcase)
			"data": {} (Data json in case if POST testcases)
		}
	}

Build the image
---------------

After the above steps are completed run

::

		make build_images

This would build the images with the changes.

Now, prepare a test suite to trigger the testcase.
