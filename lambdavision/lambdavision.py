import io

import boto3
import PIL.Image
import torch
from torch.utils import model_zoo
import torchvision

from imagenet1000 import classid_to_human


s3_client = boto3.client('s3')

valid_transform = torchvision.transforms.Compose([
    torchvision.transforms.Resize(size=256, interpolation=PIL.Image.ANTIALIAS),
    torchvision.transforms.CenterCrop(size=224),
    torchvision.transforms.ToTensor(),
])


class SetupModel(object):
    model = torchvision.models.resnet.ResNet(
        torchvision.models.resnet.BasicBlock,
        [2, 2, 2, 2])

    def __init__(self, f):
        self.f = f
        model_url = torchvision.models.resnet.model_urls['resnet18']
        self.model.load_state_dict(model_zoo.load_url(model_url,
                                                      model_dir='/tmp'))
        self.model.eval()

    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)


def predict(r):
    input_batch = []
    print('# predict: PIL transforming image...')
    with PIL.Image.open(io.BytesIO(r)) as im:
        im = im.convert('RGB')
        input_batch.append(valid_transform(im))
    print('# predict: Torching...')
    input_batch_var = torch.autograd.Variable(
        torch.stack(input_batch, dim=0), volatile=True)
    print('# predict: returning SetupModel...')
    return SetupModel.model(input_batch_var)


# download the model when servicing request and enable it to
# persist across requests in memory

@SetupModel
def s3upload(event, _):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        print('bucket={} key={}'.format(bucket, key))
        model_output = predict(
            s3_client.get_object(Bucket=bucket, Key=key)['Body'].read())
        score, classid = torch.max(model_output, 1)
        # get scalar from 1-element Tensor, convert to Python type to index
        score = float(score[0])
        classid = int(classid[0])
        print('score={} classid={} imagenet human={}'.format(
            score, classid, classid_to_human[classid]))

        # I can't figure how to get just the values of multiple scores and
        # indices, just need to learn more how to use the pytorch Tensor stuff.

        # scores_classids = torch.topk(model_output, 3)
        # print('# top3 type={} scores_classids={}'.format(
        #     type(scores_classids), scores_classids))
        # # top3 type=<class 'tuple'>
        # #    scores_classids=(
        # #      Variable containing: 9.8670  9.2123  9.0480 [torch.FloatTensor of size 1x3],
        # #      Variable containing: 489  107    6          [torch.LongTensor of size 1x3]
        # # )
        # scores, classids = scores_classids
        # print('# scores   type={} val={}'.format(type(scores), scores))
        # print('# classids type={} val={}'.format(type(classids), classids))

        # scores = scores.data
        # classids = classids.data
        # print('# data scores   type={} val={}'.format(type(scores), scores))
        # print('# data classids type={} val={}'.format(type(classids), classids))
        # length = scores.size()[0]  # should be same as our topk() request
        # print('# length={}'.format(length))
        # for i in range(length):
        #     score = scores[i]
        #     classid = classids[i]
        #     print('# score type={} val={}'.format(type(score), score))
        #     print('# classid type={} val={}'.format(type(classid), classid))
        #     # score_classid=Variable containing:
        #     #  9.8670  9.2123  9.0480
        #     # [torch.FloatTensor of size 1x3]
        #     #  type=<class 'torch.autograd.variable.Variable'>
        #     score = int(score)
        #     classid = int(classid)
        #     print('score={} classid={} imagenet human={}'.format(
        #         score, classid, classid_to_human[classid]))
