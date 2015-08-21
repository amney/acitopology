# acitopology

## Installation

acitopology requires the following packages

* Flask 
* ACI Cobra
    
Install flask using ``pip install flask``

Install Cobra via the package available on Cisco.com or locally from your APIC at ``/cobra/``

## Launching
    python topology.py --help
    usage: topology.py [-h] [-u URL] [-l LOGIN] [-p PASSWORD]
    
    optional arguments:
      -h, --help            show this help message and exit
      -u URL, --url URL     APIC IP address.
      -l LOGIN, --login LOGIN
                            APIC login ID.
      -p PASSWORD, --password PASSWORD
      
## Viewing

Visit ``http://127.0.0.1:5000``