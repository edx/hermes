#### Hermes

![hermes](Hermes.png)

### About

Hermes is the messenger/bureaucrat of the edx stack.  It fetches documents and files them on a server's filesystem on a regular basis

### Install

```
  pip install -r requirements.txt
```

### Running

Hermes is designed to run under supervisor.  It takes an unlimited number of configuration files and will poll those files in the specified interval and pull down updates based on changes of the http `Last-Modified` header.  if a file has changed, it will run a configurable command after downloading the updated file.  If you don't pass in an interval, it will download all files once and then exit.


### Permissions

Hermes writes files and executes commands, therefore he needs permission to write and execute those files and commands.  For maximum security, assign hermes his own user, execute comamnds using sudo and strictly limit the commands he's allowed to run in sudoers.

## Example sudoers file

# Todo


### Example(download unencrypted yaml over HTTPS)


```
./hermes --interval 30 \
 --filename /edx/etc/edxapp/lms.yaml --url https://s3.amazonaws.com/edx-config/prod-edx/lms.yaml --command 'sudo chown edxapp:www-data /edx/etc/edxapp/lms.yaml; sudo chmod 660 /edx/etc/edxapp/lms.yaml; sudo /edx/bin/supervisorctl restart lms' \
 --filename /edx/etc/edxapp/cms.yaml --url https://s3.amazonaws.com/edx-config/prod-edx/cms.yaml --command 'sudo chown edxapp:www-data /edx/etc/edxapp/cms.yaml; sudo chmod 660 /edx/etc/edxapp/cms.yaml; sudo /edx/bin/supervisorctl restart cms' \
```

### Example(download unencrypted yaml over S3)


```
./hermes --interval 30 \
 --filename /edx/etc/edxapp/lms.yaml --url s3://some-bucket/lms.yaml --command 'sudo chown edxapp:www-data /edx/etc/edxapp/lms.yaml; sudo chmod 660 /edx/etc/edxapp/lms.yaml; sudo /edx/bin/supervisorctl restart lms' \
 --filename /edx/etc/edxapp/cms.yaml --url s3://some-bucket/cms.yaml --command 'sudo chown edxapp:www-data /edx/etc/edxapp/cms.yaml; sudo chmod 660 /edx/etc/edxapp/cms.yaml; sudo /edx/bin/supervisorctl restart cms' \
```

### Example(download and decrypt yaml over S3)

Hermes can use https://github.com/edx/asym-crypto-yaml to decrypt yaml before writing it to the file system, you just need to provide a optional private key arg like so:

```
./hermes --interval 30 \
 --filename /edx/etc/edxapp/lms.yaml --url s3://some-bucket/lms.yaml --secret-key-file /path-to-some-rsa-private-key --command 'sudo chown edxapp:www-data /edx/etc/edxapp/lms.yaml; sudo chmod 660 /edx/etc/edxapp/lms.yaml; sudo /edx/bin/supervisorctl restart lms' \
 --filename /edx/etc/edxapp/cms.yaml --url s3://some-bucket/cms.yaml --secret-key-file /path-to-some-rsa-private-key --command 'sudo chown edxapp:www-data /edx/etc/edxapp/cms.yaml; sudo chmod 660 /edx/etc/edxapp/cms.yaml; sudo /edx/bin/supervisorctl restart cms' \
```

## Or configure via Yaml:
/edx/etc/hermes/hermes.yaml:
```
- filename: '/edx/etc/edxapp/lms.yaml'
  secret_key_file: /path-to-some-rsa-private-key  # optional
  url: 'https://s3.amazonaws.com/edx-config/prod-edx/lms.yaml'
  command:  'sudo chown edxapp:www-data /edx/etc/edxapp/lms.yaml; sudo chmod 660 /edx/etc/edxapp/lms.yaml; sudo /edx/bin/supervisorctl restart lms' 
- filename: '/edx/etc/edxapp/cms.yaml'
  secret_key_file: /path-to-some-rsa-private-key  # optional
  url: 'https://s3.amazonaws.com/edx-config/prod-edx/cms.yaml'
  command:  'sudo chown edxapp:www-data /edx/etc/edxapp/cms.yaml; sudo chmod 660 /edx/etc/edxapp/cms.yaml; sudo /edx/bin/supervisorctl restart cms' 
```

The secret_key_file is only needed if your yaml is encrypted
If you dont pass a key, but include encrypted values they will be deserialized as their encrypted values instead of decrypting them

Then run:
```
./hermes.py -y /edx/etc/hermes/hermes.yaml -i 10
```


### Options

run --help to get a list of options
