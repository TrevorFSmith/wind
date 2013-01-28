from django.contrib.sites.models import Site

def site(request):
    """Adds context variables to every request"""
    current_site = Site.objects.get_current()
    host_name = current_site.domain
    if ':' in host_name: host_name = host_name.split(':')[0]

    return {
    	'site': current_site,
    	'host_name': host_name
    }

# Copyright 2012 Trevor F. Smith (http://trevor.smith.name/) 
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
