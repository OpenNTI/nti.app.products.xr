============================
 nti.app.products.xr
============================

This package provides a prototype CMI5 AU that can work with an
installed launcher application to launch content on an android based
headset. It currently has a depenency on dataserver but in theory it
could be a small standalone pyramid project if we wanted to deploy the
AU as a standalone service. As we may likely want something more first
order than CMI5 based integration in the future we leave this hefty
dependency in place for now.

Overview
--------

The XR experiences we are building are part of a larger learning
environment hosted on our LMS. Users access learning objects in our
web/mobile LMS. When they encounter XR content we need to facilitate
getting the user into the VR headset, getting them in the proper
experience, and providing the necessary data to track completion and
other analytics. Input mechanisms on VR headsets are a bit of a pain,
so having to require users to input long usernames/passwords is not an
ideal user experience. Aaron's ideal linking is for the XR content to
present some instructions in the LMS that direct the user to the
application, along with a short code that can be easily input into the
VR headset. The rest as they say is magic.

Right now our completion and analytics tracking are all
bespoke. Content presentation and launching mechanisms are bespoke,
etc. While we could build out all the pieces to make this happen
"natively" it increases the work required on the LMS client and the
LMS back end.  If we can figure out how to leverage SCORM/xAPI to
launch the experiences we can eliminate a potential large amount of
development work on the LMS UI and back end needed for the
prototype. The idea being we can just leverage the existing ScormCloud
code to handle launch, presentation, and completion
automatically. We've then reduced the problem to 3rd party content
that does device hand off.

SCORM creates challenges because the interaction of the API happens
solely through the browser. So while we can probably work the launch
out getting any data back to the LMS on completion is going to be a
challenge at best.

XAPI (specifically CMI5 launches) on the other hand is designed to
work with any system that can communicate via REST. This is attractive
for a few reasons. It's much easier to facilitate getting data back to
the LMS. Likewise if we can get the launch data to the headset, in
theory it has everything the VR experience would need. It's possible
we can completely bypass the authentication for now (CMI5 gets the
credentials to the headset we would need for xAPI).

In short, the `CMI5 launch flow <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#content_launch>`_, initiates a content launch for a
specified Assignable Unit (AU) at a given `launch url <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#url>`_. The launch URL
can be a page packaged with the CMI5 content, or it can be a fully
qualified url hosted by another system. The launch url is provided
information about the LRS, a mechanism to retrieve credentials for
interacting with the LRS, basic information about the user launching
the AU, and indirectly via the xAPI State API information about the
content being launched. The problem space then becomes how to perform
device hand off from our AU to the headset with appropriate information
and context.

Details
-------

The idea is as follows:

1. Create a CMI5 AU for each VR experience. This will encapsulate the
   information necessary to launch the proper experience (apk bundle,
   scene, etc.).

2. Create a NextThought hosted launch url that the aforementioned AU's
   will launch from. This launch url will capture the CMI5 launch data
   and store it behind a one time use short lived code. The AU will
   then present instructions to the user to launch an application on
   their headset and provide the code both in textual and qr code form.

3. The user will launch the specified XR app in their headset and enter
   the short code, or scan the QR code using the front facing camera.

4. The XR app will then exchange the short code for launch information
   using a well known (predetermined) API.

5. The XR app will then use the provided launch information to take
   over the CMI5 flow, sending all necessary CMI5 statements.

In the scenario above the discussed flow has the XR app acting as both
one side of the hand off and as the target learning scenario. In
practice we can separate this responsibility into a launcher
application on the headset and a learning application. This separation
would allow us to launch 3rd party content on the headset we don't
own. This is the path we will go down now, although it's easy to
imagine the learning scenario we author doing the hand off without a
launcher application.

It's all worth noting that the code based hand off is somewhat similar
to the OAuth 2.0 device flow, but in this case things are
backwards. Rather than them getting a code from the headset and typing
it into the web browser, we are giving them a code in the web browser
and they are entering it in the headset. We're trying to minimize the
number of times the user has to come in and out of the headset. An
obvious issue is that the code is going to be visible on screen and
could be scooped up by any interesting party. Anyone that sees the
code could in theory exchange it for the launch information which
includes a token that can be used to generate statements on behalf of
the actor. That's not great, but we can limit it to one time use, with
a very short time (2 minutes) and the token provided doesn't really
let someone do anything nefarious. The token vended is supposed to be
scoped to only what is required to store data. Additionally I think
there are ways to mitigate risk here, we could for example, detect if
you are launching to a new device and challenge back in the app. We
could take a page out of OAuth device flow and generate codes that
only work with an identifier of the device. That obviously requires a
pre-step where we link devices to users. I don't think we need that
for a first version.

Our goal will be that CMI5 content encapsulates all the information
required for our AU's launch url to direct the user into the
appropriate learning content. The `course structure <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#130-course-structure-data-requirements>`_ primarily
communicates this information via the AU `launchParameters meta
data <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#130-course-structure-data-requirements>`_. This is defined as a string, though is it commonly a json encoded string.

.. code:: xml
    :name: Example cmi5.xml for our scenario

    <?xml version="1.0" encoding="utf-8"?>
    <courseStructure xmlns="https://w3id.org/xapi/profiles/cmi5/v1/CourseStructure.xsd">
      <course id="https://nextthought.com/courses/course1/experiences/aspire">
        <title>
          <langstring lang="en-US">ASPIRE</langstring>
        </title>
        <description>
          <langstring lang="en-US">
    	Super cool aspire demo.
          </langstring>
        </description>
      </course>
      <au id="https://nextthought.com/courses/course1/experiences/aspire">
        <title>
          <langstring lang="en-US">ASPIRE ILEETA</langstring>
        </title>
        <description>
          <langstring lang="en-US">
    	This course will introduce you into the basics of geology. This includes subjects such as
    	plate tectonics, geological materials and the history of the Earth.
          </langstring>
        </description>
        <url>https://aspire.nextthought.io/datserver2/@@launch_xr</url>
        <launchParameters>
          {"bundleId": "com.nextthought.aspire", "extras": {"scene": "pawnshop"}, "cmi5": true}
        </launchParameters>
      </au>
    </courseStructure>


The roll of the AU launch url
`https://aspire.nextthought.io/datserver2/@@launch_xr <https://aspire.nextthought.io/datserver2/@@launch_xr>`_ becomes device
handoff. If we successfully capture all necesary data in the CMI5
course structure this becomes generic for any application that knows
how to be launched in the context of our AU. The launch url will be
hosted by the LMS back end. It will receive the standard `CMI5 launch parameters <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#launch_method>`_.

The AU will resolve the LRS credentials by performing the
`Authorization Token Fetch <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#launch_method>`_. It will then fetch the `LMS.LaunchData state <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#100-xapi-state-data-model>`_
data. The AU will temporarily store this information in Redis beneath
a one-time-use shortlived alphanumeric code such as A3X56Y. The code
will be presented in the browser with instructions to launch the XR Launcher App.

**Note** The code will initially be a 6 character string from the `Z
Base-32 alphabet <https://philzimmermann.com/docs/human-oriented-base-32-encoding.txt>`_ (case insensitive).

The XR launcher App is responsible for taking the code as input from
the user. The user should have the option to key in the code, or to
read it via qr code on headsets that support accessing the front facing
camera. The code can be exchanged by performing a json POST of the form:

**Note** the url may change, but the request / response details should remain the same

::

    POST /dataserver2/@@launch_xr_handoff HTTP/1.1
    Accept: application/json, */*;q=0.5
    Accept-Encoding: gzip, deflate
    Connection: keep-alive
    Content-Length: 18
    Content-Type: application/json
    Host: aspire.nextthought.io
    User-Agent: HTTPie/2.4.0

    {
        "code": "3aye4a"
    }

The response of which will be a json body if the code is valid.

.. code:: json

    {
        "activityId": "http://cloud.scorm.com/cmi5/lms-id/2536d67eb0f262376e0601229c18db4bfac48bca/15ebf33d-cf80-4c3e-bce7-22b51176c491",
        "actor": {
    	"account": {
    	    "homePage": "http://cloud.scorm.com",
    	    "name": "URV3M3KDEU|chris.utz@nextthought.com"
    	},
    	"name": "chris utz",
    	"objectType": "Agent"
        },
        "endpoint": "https://cloud.scorm.com/lrs/URV3M3KDEU/",
        "href": "/dataserver2/@@launch_aspire_handoff?code=yfy9kp",
        "launchData": {
    	"contextTemplate": {
    	    "contextActivities": {
    		"grouping": [
    		    {
    			"id": "https://aspire.nextthought.io/identifiers/courses/aspire",
    			"objectType": "Activity"
    		    }
    		],
    		"parent": [
    		    {
    			"id": "https://aspire.nextthought.io/identifiers/courses/aspire",
    			"objectType": "Activity"
    		    },
    		    {
    			"id": "http://cloud.scorm.com/cmi5/lms-id/2536d67eb0f262376e0601229c18db4bfac48bca/7c88fdfa-140c-4eb8-8ef9-a3b4be0fb456",
    			"objectType": "Activity"
    		    }
    		]
    	    },
    	    "extensions": {
    		"https://w3id.org/xapi/cmi5/context/extensions/sessionid": "d556e6db-d91b-4fc2-8fce-337248be0210"
    	    }
    	},
    	"entitlementKey": {},
    	"launchMethod": "AnyWindow",
    	"launchMode": "Normal",
    	"launchParameters": {"bundleId": "com.nextthought.aspire", "extras": {"scene": "pawnshop"}, "cmi5": true},
    	"moveOn": "NotApplicable",
    	"returnURL": " https://cloud.scorm.com/ScormEngineInterface/defaultui/player/intermediate.html?cache=20.1.21.607&preventRightClick=false&ieCompatibilityMode=none&configuration=FDTqEZFQBkkHLqvn9hCuxAaZHYP8zqBdKxLxaXOR-8rqZeVdxfiLARvjIMgoMGxljkAzos7gaZemcMxg5hOpNJEqbGKdu6vrbzhtVK_2cgR820ZqiQLxOVyeL2QEgio7EKE3ujf97dfTFwfHqZZOZDxedSgxgeS_RMqwBqcVaZBkoVgdCKXh04zV3DwFe0vRMk-kC0ukYFh2mCJyu4FHYX5XmAkLsVpYKlOWhE6M_-jgiZGqyURDBJ8koKNK79nJXZWFrvlX7QLZbMx_KZsd6DoK92OlGx4m0O-f7Q2WhrZE9INv5J7_xP84jNMJf4ENe9B5iEtsHnbgx4sNl6ofRoQJUmcQ-G8z0J-5zpWuca3ICIIgAz0i_YV4kjd4RfbSj7P_UHja1fgVLsbvVww_xaFkcWwStYU1RKRIx7fn4RV2e7_wXcTOmw_a8T0Zf8YctZMDGypdX026n2vlkSrpOMrM3Cc18Dr-60_PWcA-TwCkeIyqDIniI8XZsermREI0LBNaGvRvno5iloVntwrsf6HvEqzPP8gh_dQEHdQG7YEAme2ntlvOZS4p7JbxINly2mQgUUeeE3KhLOh-WHjT6cKhqJXFlYfLrPfOxZtoIFv0uUz_bs2cbQu8vb2j1lVQi3Zb3d1YdXtsGkJEWn7_axEs-phGmqX4_6lgb2WuJWvMEngYMw3hcFCmR-9lX8l2l7UwoMDWTrPzyJtbns5rpWqDfNg31Q80v5BJix-toOYCyRYEGQe_sK3-5j4WwkCKVbrckDG3fo0Oa2AhHKKWtR5gmdEFNSMAI4ad8arrkKl5dXplMjgqy8l2tkiZ23tiWw2Ncie2_R2u5RtLQkjp-L-_Lo-SVTNb_H7yb8IbhWeuizHqiwfvGD_QDzfgU5zp8GkpleUTTN55igDoiy_ycqcFGmfk8k2ixPvho-9Z-SFLJd8kXpPjTivU8ii-tbHOBraR1af2xRth4w5tO9ZZPgI8v2kv&cc=en_US"
        },
        "registration": "4acdaa92-0d85-46e9-b76f-3b37fe956584",
        "token": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
    }

The Launcher will then inspect the provided data and launch the
requested bundleId. When appropriate the launcher may pass additional
extras from the launchParameters or in the case of content that supports
CMI5 the entire launch data.

Scenarios the support CMI5 are responsible for sending fulfilling all
the `CMI5 AU Requirements <https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#au_requirements>`_. This includes sending the required first
statement, last statement, and any other CMI5 defined and allowed
statements using the provided contextTemplate and actor.

