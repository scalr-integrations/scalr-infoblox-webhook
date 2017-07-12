# Scalr-Infoblox webhook

This webhook enables you to register Scalr-managed virtual machines in Infoblox.

## Setup instructions

#### Webhook handler setup

##### On Centos 7 / RHEL 7

- Install the required packages:
```
yum install epel-release
yum install git gcc python python-devel python-pip uwsgi uwsgi-plugin-python
```
- Retrieve the webhook code:
```
mkdir -p /opt/infoblox-webhook
cd /opt/infoblox-webhook
git clone https://github.com/scalr-integrations/scalr-infoblox-webhook.git .
```
- Install the Python dependencies
```
pip install -r requirements.txt
```
- Configure uwsgi to serve the webhook
```
cp uwsgi.ini /etc/uwsgi.d/infoblox-webhook.ini
chmod uwsgi:uwsgi /etc/uwsgi.d/infoblox-webhook.ini
systemctl enable uwsgi
```

#### Scalr webhook setup

Log into Scalr at the global scope, and click on Webhooks in the main menu.
In the Endpoints section, create a new endpoint with URL: `http://<server-ip>:5000/infoblox/`

Note down the signing key that Scalr generated, we will need it later.


Then in the Webhooks section, create a new webhook with the following settings:
- Name: Infoblox integration
- Endpoints: Select the endpoint you just created
- Events: HostUp, BeforeHostTerminate, HostDown
- Farms: leave empty
- Timeout: 10 seconds
- Max. delivery attempts: 3

and click on Save to create the webhook.


#### Webhook configuration

Edit the `config.json` file and set the Scalr signing key, infoblox host as well as valid credentials for Infoblox.

Reload the configuration with:
```
systemctl restart uwsgi
```

## Testing and troubleshooting

The uwsgi logs are appended to `/var/log/messages`.

To check that the web server is serving our webhook, run the following command on the webhook server:
```
curl -XPOST http://localhost:5000/infoblox/
```

You should get a 403 error, because our request was not signed. If that is not the case, check for errors in the uwsgi logs.

The next test is to launch an instance in Scalr. When it comes up, the webhook should be called and the new host should be registered in Infoblox. When the instance is terminated, the host should be removed from Infoblox. If that is not the case, check for errors in the uwsgi logs.




