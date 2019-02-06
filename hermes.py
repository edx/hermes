#! /usr/bin/env python3

import sys
import subprocess
import click
import time
import requests
import yaml
import logging


# ./hermes --interval 30
# --filename index.html --url https://edx.org/index.html --command /edx/bin/supervisorctl restart lms 
# --filename index2.html --url https://edx.org/index2.html --command /edx/bin/supervisorctl restart cms 
# --filename index3.html --url https://edx.org/index3.html --command /edx/bin/supervisorctl restart discovery 

@click.command()
@click.option('--debug/--no-debug', default=False)
@click.option('--filename', '-f', type=str, help='filename to write to', multiple=True)
@click.option('--url', '-u', type=str, help='url to read from', multiple=True)
@click.option('--command', '-c', type=str, help='command to run', multiple=True)
@click.option('--interval', '-i', type=int, help='frequency to poll all configured files, in seconds')
@click.option('--yamlfile', '-y', type=click.Path())
def watch_config(filename, url, command, interval, debug, yamlfile):
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG if debug else logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    try:
        if yamlfile:
            with open(yamlfile) as yamlhandle:
                service_config = yaml.load(yamlhandle)
        elif len(filename) == len(url) and len(filename) == len(command):
            service_config = []
            for filename_item, url_item, command_item in zip(filename, url, command):
                service_config.append({'filename': filename_item, 'url': url_item, 'command': command_item})
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
            assert filename_item != None
            assert url_item != None
            assert command_item != None
            if check_config_age(filename_item, url_item, file_timestamps):
                download_config(filename_item, url_item, file_timestamps)
                logging.info('file \'%s\' changed, running: \'%s\'' % (filename_item, command_item))
                logging.info(subprocess.check_output(command_item, shell=True).decode("utf-8"))

        if interval == 0:
            break
        time.sleep(interval)
        seconds = seconds + interval
        logging.debug('DEBUG: woke up after %d seconds\n' % seconds)


def check_config_age(filename, url, file_timestamps):
    if file_timestamps.get(filename):
        try:
            url_head = requests.head(url, timeout=2)
        except requests.exceptions.RequestException as err:
            logging.error('ERROR checking %s: %s\n' % (str(url), str(err)))
            # If we can't head the file, log an error and continue
            return False
        if url_head.headers['Last-Modified'] != file_timestamps[filename]:
            logging.debug('DEBUG: changed %s Server modified: %s Local modified: %s\n' % (url, url_head.headers['Last-Modified'], file_timestamps[filename]))
            return True
        else:
            logging.debug('DEBUG: Unchanged %s\n' % url)
            return False
    else:
        # on the first time seeing a file, we always update
        return True

def download_config(filename, url, file_timestamps):
        try:
            url_get = requests.get(url, timeout=2)
        except requests.exceptions.RequestException as err:
            logging.error('ERROR downloading %s: %s\n' % (str(url), str(err)))
            return False
        try:
            filehandle = open(filename, "w")
            filehandle.write(str(url_get.content)) 
            filehandle.close()
            file_timestamps[filename] = url_get.headers['Last-Modified']
        except IOError as err:
            logging.error('ERROR writing %s: %s\n' % (str(filename), str(err)))
            return False
        logging.info('Downloaded %s\n' % url)
        return True

if __name__ == '__main__':
    watch_config()
