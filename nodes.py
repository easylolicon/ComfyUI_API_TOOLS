import hashlib
import io
import json
import logging
import socket
import uuid

import requests
from qcloud_cos import CosConfig, CosS3Client
from datetime import datetime
from PIL import Image


class UPLOAD_IMAGES_TO_COS:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'images': ('IMAGE',),
                'region': ('STRING', {'multiline': False}),
                'secret_id': ('STRING', {'multiline': False}),
                'secret_key': ('STRING', {'multiline': False}),
                'bucket': ('STRING', {'multiline': False}),
                'scheme': ('STRING', {'multiline': False, 'default': 'http'}),
                'domain': ('STRING', {'multiline': False}),
                'base_dir': ('STRING', {'multiline': False, 'default': '/comfyui/output/__DATE__/'}),
            },
        }

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('urls_dic_text',)
    FUNCTION = 'execute'
    CATEGORY = 'API_Tools'

    def execute(self, images, region, secret_id, secret_key, bucket, scheme, domain, base_dir):
        if domain == '':
            domain = None
        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Scheme=scheme, Domain=domain)
        client = CosS3Client(config)
        base_dir = base_dir.replace('__DATE__', datetime.now().strftime('%Y-%m-%d'))

        image_urls = []
        for image in images:
            # 将 tensor 图片 转化为 PIL 图片
            image = Image.fromarray(image.mul(255).byte().numpy(), mode='RGB')

            # 将图像数据保存为 jpg 格式的文件对象
            byte_io = io.BytesIO()
            image.save(byte_io, format='JPEG')

            # 获取文件对象的全部内容
            image_bytes = byte_io.getvalue()
            # 创建 存储对象路径
            filepath = base_dir + hashlib.md5(image_bytes).hexdigest() + '.jpg'
            client.put_object(Bucket=bucket, Key=filepath, Body=image_bytes)
            image_urls.append(config.uri(bucket=bucket, path=filepath))

        return (json.dumps(image_urls),)


class AUTO_CALLBACK_API:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'images_dic_text': ('STRING', {'multiline': False, "forceInput": True, }),
                'callback_url': ('STRING', {'multiline': False, 'default': 'https://www.baidu.com/test/test'}),
                'headers_dic_text': ('STRING', {'multiline': False, 'default': '{}'}),
                'params_dic_text': ('STRING', {'multiline': False, 'default': '{}'}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ('string',)
    FUNCTION = 'execute'
    CATEGORY = 'API_Tools'

    def execute(self, images_dic_text, callback_url, headers_dic_text, params_dic_text):
        # 参数重建
        params_dic = json.loads(params_dic_text)
        params_dic['comfyui_result'] = {"images": json.loads(images_dic_text)}
        params_dic['service_name'] = socket.gethostname()
        params_dic['service_ip'] = socket.gethostbyname(params_dic['service_name'])
        params_dic['request_id'] = str(uuid.uuid4())
        # 请求头重建
        headers_dic = json.loads(headers_dic_text)
        for try_num in range(0, 3):
            try:
                # 请求日志
                logging.info(json.dumps({'callback_url': callback_url, 'headers': headers_dic, 'params': params_dic, }))
                # 发起请求
                response = requests.request(method='POST', url=callback_url, headers=headers_dic, json=params_dic, timeout=10, verify=False)
                res_dic = json.loads(response.text)
                if response.status_code != 200 or res_dic is None or res_dic.get('code') != 10000:
                    raise Exception(json.dumps({'error': '请求异常', 'status_code': response.status_code, 'text': response.text, 'params': params_dic}))
                # 否则返回成功
                return ('request success',)
            except Exception as e:
                logging.error(json.dumps({'request_id': params_dic['request_id'], 'error': str(e)}))
        # 返回失败
        return ('request fail',)


NODE_CLASS_MAPPINGS = {
    'UPLOAD_IMAGES_TO_COS': UPLOAD_IMAGES_TO_COS,
    'AUTO_CALLBACK_API': AUTO_CALLBACK_API,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    'UPLOAD_IMAGES_TO_COS': 'upload images to cos',
    'AUTO_CALLBACK_API': 'auto callback api',
}
