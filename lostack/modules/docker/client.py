import docker

def get_services_info(names:list):
    client = docker.APIClient()
    containers = client.containers(all=True)
    mapped_containers = {}
    for c in containers:
        name = c["Names"][0].strip("/")
        mapped_containers[name] = c
    info = {}
    for n in names:
        info[n] = mapped_containers.get(n)
    return info