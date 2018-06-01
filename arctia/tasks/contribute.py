class Contribute(object):
    def __init__(self, entity, job, finished_proc):
        self.entity = entity
        self.job = job
        self.finished_proc = finished_proc

    def enact(self):
        self.job['collected_goods'].append(self.entity)
        self.finished_proc()
