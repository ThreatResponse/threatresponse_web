from docker import Client

class DockerClient(object):
    def __init__(self):
        self.client = self.__initialize

    def __initialize(self):
        try:
            cli = Client(base_url='unix://var/run/docker.sock')
        except:
            raise "Problem getting attached to docker socket."
        return cli

class DockerControl(object):
    def __init__(self):
        self.client = DockerClient().client

    def containers(self):
        containers = self.client().containers()
        return containers

    def container(self, container_name):
        container = self.client().containers(container_name)
        return container

    def create_command(self, container, command):
        docker_command = self.client().exec_create(container, command, tty=True)
        return docker_command

    def start_command(self, command):
        docker_command_status = self.client().exec_start(command, detach=True, tty=True, stream=True)
        return docker_command_status


class TimeSketchControl(object):
    def __init__(self):
        self.client = DockerClient().client
        self.container_id = self.timesketch_container()

    def import_plaso_file(self, plaso_file):
        control = DockerControl()
        psort_string = "psort.py -o timesketch /tmp/{plaso_file} --name {plaso_file}".format(plaso_file=plaso_file)
        docker_command = control.create_command(self.container_id, psort_string)
        control.start_command(docker_command)
        pass

    def timesketch_container(self):
        ts = self.client().containers('timesketch')
        return ts[0]['Id']
