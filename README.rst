=====================
 README LambdaVision
=====================

This is a project to do image recognition using AWS Lambda
and the `Serverless Framework <https://serverless.com/>`_.

It's totally derived from a blog post by Michael Diets entitled
`"Serverless deep/machine learning in production -- the pythonic way"
<https://blog.waya.ai/deploy-deep-machine-learning-in-production-the-pythonic-way-a17105f1540e>`_.


Building Prerequisites: Makefile, Docker
========================================

In the post, Michael uses a script to build `PyTorch
<http://pytorch.org/>`_ and its prerequisites, some of which are
C-based. Those require compilation on a Lambda-compatible machine. I
wanted something a bit more automated, so I've turned that build into
a `Makefile <Makefile>`_ which builds inside the enormously useful
`lambci docker image <https://github.com/lambci/docker-lambda>`_.

Warning: The build needs over 2GB RAM, and macOS Docker ran out of
memory while copiling, with GCC reporting this inscrutable message::

  error: command 'gcc' failed with exit status 4

I increased it by going to the Docker icon in my menubar, Preferences,
Advanced, and setting the RAM to 4GB, then restarting Docker.

I wanted to commit the binaries and built Python libraries to this Git
repo, but one of the compiled libraries was too big for Git::

  remote: error:
  File lambdavision/torch/_C.cpython-36m-x86_64-linux-gnu.so is 105.86 MB;
  this exceeds GitHub's file size limit of 100.00 MB

So you're stuck building the prerequisites yourself.  Since this build
can take 11 minutes on my MacBookPro, the Makefile tries to be smart
about not building stuff it sees is already there.

After building each piece, the Makefile puts everything in the
`Serverless Framework <https://serverless.com/>`_ service directory,
``lambdavision``.

Use the Serverless Framework to Make Life Easier
================================================

Michael's build process creates a ZIP bundle which can be uploaded to
AWS Lambda, but then you're on your own to create S3 buckets,
triggers, permissions and so on. I'm lazy, so I specify all this stuff
in my `serverless.yml <lambdvision/serverless.yml>`_ file. Then I can
deploy my Lambda function along with all the requisite PyTorch
binaries and libraries in one step::

  sls deploy

Normally, with Serverless, you can redeploy the function by itself,
without having to rebuild any of the infrastructure like::

  sls deploy function --function lambdavision

Unfortunately, AWS has limit on size which we exceed::

  Serverless: Packaging function: lambdavision...
  Serverless: Excluding development dependencies...
  Serverless: Uploading function: lambdavision (66.79 MB)...
  Serverless Error ---------------------------------------
  Request must be smaller than 69905067 bytes for the UpdateFunctionCode operation

So you have to do the full ``deploy`` each time; it's not a big deal,
because AWS knows the CloudFormation-based infrastructure hasn't
changed.

Update the Lambda Function to be More Descriptive
=================================================

Michael's original Lambda function simply returned the
``model_output``, which is a 1000-element tensor.  But in Lambda,
async functions don't "return" anything to the user so there was no
output.  I printed it, and the prints get sent to the AWS CloudWatch
logs, which Serverless lets you watch easily with::

  sls logs --tail --function lambdavision &

That output tensor, truncated in the display, didn't tell me anything
useful; it appeared to be just a list of scores -- how well each
pre-trained model classification matched the submitted image.  I dug
around a while and determined that the model was pre-trained on an
ImageNet sample of 1000 images; some more sleuthing turned up a useful
`class-id to human-name mapping
<https://gist.github.com/yrevar/942d3a0ac09ec9e5eb3a>`_. I've never
played with PyTorch or tensors before so it took me a while to figure
out how to index the best score, but now it displays the score, index,
and human friendly class name.

We can use the AWS CLI to upload a picture to S3::

  s3 cp ~/Downloads/squirrel.jpg    s3://chris-lambdavision/

and watch what it reports in the tailed logs::

  score=9.418614387512207 classid=335 imagenet human=fox squirrel, eastern fox squirrel, Sciurus niger

If upload a picture of myself wearing a big white hat and it says::

  score=9.719132423400879 classid=515 imagenet human=cowboy hat, ten-gallon hat

I can upload a picture of an audio tape cassette found on the net and it says::

  score=13.65023136138916 classid=481 imagenet human=cassette

It took about 8 seconds of Lambda-time to do this::

  REPORT RequestId: bd4c7ded-23cb-11e8-ba21-2116960e04ca
  Duration: 8073.79 ms	Billed Duration: 8100 ms
  Memory Size: 2048 MB	Max Memory Used: 276 MB

It's not `AWS Rekognition <https://aws.amazon.com/rekognition/>`_ but
it works.

Our future work will require training models based on specific and
unusual subject matter which our client deems sensitive, so
Rekognition may not be a viable option for us, and this Lambda-based
classifier shows some promise... or at least a start.
