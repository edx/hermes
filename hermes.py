#! /usr/bin/env python3

import sys
import subprocess
import click
import time
import requests
import yaml
import logging
import boto3
import backoff
from itertools import zip_longest
import asym_crypto_yaml
from enum import Enum

class Protocol(Enum):
    https = 1
    s3 = 2

valid_protocols = []
for protocol in Protocol:
    valid_protocols.append(protocol)

# ./hermes --interval 30
# --filename index.html --url https://edx.org/index.html --command /edx/bin/supervisorctl restart lms 
# --filename index2.html --url https://edx.org/index2.html --command /edx/bin/supervisorctl restart cms 
# --filename index3.html --url https://edx.org/index3.html --command /edx/bin/supervisorctl restart discovery 

@click.command()
@click.option('--debug/--no-debug', default=False)
@click.option('--filename', '-f', type=str, help='filename to write to', multiple=True)
@click.option('--url', '-u', type=str, help='url to read from', multiple=True)
@click.option('--command', '-c', type=str, help='command to run', multiple=True)
@click.option('--interval', '-i', type=int, help='frequency to poll all configured files, in seconds', default=60)
@click.option('--yamlfile', '-y', type=click.Path())
@click.option('--secret-key-file', '-k', type=str, help='secret key for decrypting downloaded yaml file', multiple=True)
def watch_config(filename, url, command, interval, debug, yamlfile, secret_key_file):
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG if debug else logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    try:
        if yamlfile:
            with open(yamlfile) as yamlhandle:
                service_config = yaml.load(yamlhandle)
                # If no keys were passed, dont fail, just dont decrypt
                # This is so hermes can function with no keys being passed.
                for block in service_config:
                    if 'secret_key_file' not in block:
                        block['secret_key_file'] = None
        elif len(filename) == len(url) and len(filename) == len(command):
            service_config = []
            for filename_item, url_item, command_item, secret_key_file_item in zip_longest(filename, url, command, secret_key_file):
                block = {'filename': filename_item, 'url': url_item, 'command': command_item, 'secret_key_file': secret_key_file_item}
                service_config.append(block)
        else:
            raise Exception('ERROR parsing config')

    except Exception as err:
        raise Exception('ERROR parsing config: %s\n' % (str(err))) 
    seconds = 0
    file_timestamps = {}
    while True:
        for config_file in service_config:
            filename_item = config_file['filename']
            url_item = config_file['url']
            command_item = config_file['command']
            secret_key_file_item = config_file['secret_key_file']
            assert filename_item != None
            assert url_item != None
            assert command_item != None

            protocol = get_valid_protocol_from_url(url_item)

            if protocol == Protocol.https and config_age_changed_https(filename_item, url_item, file_timestamps):
                download_config_https(filename_item, url_item, file_timestamps, secret_key_file_item)
                run_command_for_filename(filename_item, command_item)
            elif protocol == Protocol.s3 and config_age_changed_s3(filename_item, url_item, file_timestamps):
                download_config_s3(filename_item, url_item, file_timestamps, secret_key_file_item)
                run_command_for_filename(filename_item, command_item)
            elif protocol in valid_protocols:
                # Dont do anything - this is a valid protocol, that does not need to be updated, this is
                # correct behaviour
                logging.debug("No update needed.")
            else:
                # I dont know how to compare timestamps and/or download files of this protocol
                logging.error('ERROR: unimplemented protocol %s\n' % protocol)

        if interval == 0:
            break
        time.sleep(interval)
        seconds = seconds + interval
        logging.debug('DEBUG: woke up after %d seconds\n' % seconds)

def run_command_for_filename(filename_item, command_item):
    logging.info('file \'%s\' changed, running: \'%s\'' % (filename_item, command_item))
    logging.info(subprocess.check_output(command_item, shell=True).decode("utf-8"))

def get_valid_protocol_from_url(url):
    if url.startswith("https://"):
        return Protocol.https
    elif url.startswith("s3://"):
        return Protocol.s3
    else:
        raise Exception('ERROR Unsupported Protocol')


def config_age_changed_https(filename, url, file_timestamps):

    if file_timestamps.get(filename) == None:
        return True

    try:
        url_head = requests.head(url, timeout=2)
    except requests.exceptions.RequestException as err:
        logging.error('ERROR checking %s: %s\n' % (str(url), str(err)))
        # If we can't head the file, log an error and continue
        return False
    if url_head.headers['Last-Modified'] != file_timestamps.get(filename):
        logging.debug('DEBUG: changed %s Server modified: %s Local modified: %s\n' % (url, url_head.headers['Last-Modified'], file_timestamps[filename]))
        return True
    else:
        logging.debug('DEBUG: Unchanged %s\n' % url)
        return False

def download_config_https(filename, url, file_timestamps, secret_key_file):
    try:
        url_get = requests.get(url, timeout=2)
    except requests.exceptions.RequestException as err:
        logging.error('ERROR downloading %s: %s\n' % (str(url), str(err)))
        return False
    try:
        last_modified = url_get.headers['Last-Modified']
        encrypted_filename = filename + ".enc"
        filehandle = open(encrypted_filename, "w")
        filehandle.write(str(url_get.content)) 
        filehandle.close()
        decrypt_and_write_to_file(encrypted_filename, filename, secret_key_file)
        file_timestamps[filename] = last_modified
    except IOError as err:
        logging.error('ERROR writing %s: %s\n' % (str(filename), str(err)))
        return False
    logging.info('Downloaded %s\n' % url)
    return True

def config_age_changed_s3(filename, url, file_timestamps):
    if file_timestamps.get(filename) == None:
        return True

    client = boto3.client('s3')

    # URl is expected to be something like: s3://my-bucket-name/my-path/to/my/object

    bucket_and_key = extract_bucket_key_from_s3_url(url)
    bucket = bucket_and_key['bucket']
    key = bucket_and_key['key']

    try:
        head=client.head_object(Bucket=bucket, Key=key)
    except Exception as err:
        logging.error('ERROR checking %s: %s\n' % (str(url), str(err)))
        # If we can't head the file, log an error and continue
        return False

    if head['LastModified'] != file_timestamps.get(filename):
        logging.debug('DEBUG: changed %s Server modified: %s Local modified: %s\n' % (url, head['LastModified'], file_timestamps[filename]))
        return True
    else:
        logging.debug('DEBUG: Unchanged %s\n' % url)
        return False

def download_config_s3(filename, url, file_timestamps, secret_key_file):
    client = boto3.client('s3')

    bucket_and_key = extract_bucket_key_from_s3_url(url)
    bucket = bucket_and_key['bucket']
    key = bucket_and_key['key']
    last_modified = client.head_object(Bucket=bucket, Key=key)['LastModified']

    try:
        encrypted_filename = filename + ".enc"
        with open(encrypted_filename, 'wb') as data:
            client.download_fileobj(bucket, key, data)
        decrypt_and_write_to_file(encrypted_filename, filename, secret_key_file)
        file_timestamps[filename] = last_modified

    except IOError as err:
        logging.error('ERROR writing %s: %s\n' % (str(filename), str(err)))
        return False
    except Exception as err:
        logging.error('ERROR downloading %s: %s\n' % (str(url), str(err)))
        return False
        
    logging.info('Downloaded %s\n' % url)
    return True

def extract_bucket_key_from_s3_url(url):
    # strip protocol
    bucket_and_key = url.split("//")[1]

    # Split out bucket and key
    bucket_and_key = bucket_and_key.split("/", 1)

    bucket = bucket_and_key[0]
    key = bucket_and_key[1]
    return {'key': key, 'bucket': bucket}

def decrypt_and_write_to_file(encrypted_filename, decrypted_output_filename, secret_key_file):
    decrypted_dict = None
    with open(encrypted_filename, "r") as f:
        decrypted_dict = asym_crypto_yaml.load(f, secret_key_file)
    asym_crypto_yaml.write_dict_to_yaml(decrypted_dict, decrypted_output_filename)

if __name__ == '__main__':
    watch_config()
