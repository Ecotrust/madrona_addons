from models import URLtoTaskID
from djcelery.models import TaskMeta
from django.template.loader import render_to_string

'''
NOTES:
    url entries should be unique -- a single url maps to a single task_id in a one-to-one fashion
    this strategy allows the asynchronous models to serve as a cache for those apps that wish to use it as such

    begin_process assumes that the caller wants a new process to be run,
        even if the process has already been run
        even if the process has started, but not finished
    this way polling urls can remain unique
    if the caller wants the process to be run ONLY IF it hasn't been run already,
        the caller should first check with process_exists_in_cache
'''
#should also add a task_kwargs parameter in case the task has keyword parameters
def begin_process(polling_url, task_method, task_args, cache_results=True):
    #see if task exists already
    try:
        URLtoTaskID.objects.get(url=polling_url).delete()
    except:
        pass
    #initialize task
    task = task_method.delay(*task_args)
    if cache_results:
        URLtoTaskID(url=polling_url, task_id=task.task_id).save()
    return task.task_id

#should also add a task_kwargs parameter in case the task has keyword parameters
def check_pending_or_begin(polling_url, task_method, task_args, cache_results=True):
    if process_is_pending(polling_url):
        return render_to_string('already_processing.html', {})
    else:
        begin_process(polling_url, task_method, task_args, cache_results)
        return render_to_string('starting_process.html', {})
  
#returns boolean based on process.status == 'PENDING' or 'SUCCESS' (pending or complete)
def process_is_pending_or_complete(polling_url=None, task_id=None):
    if process_is_pending(polling_url, task_id) or process_is_complete(polling_url, task_id):
        return True
    else:
        return False
  
#returns boolean based on whether process is in cache but not yet complete
def process_is_pending(polling_url=None, task_id=None):
    result = __get_asyncresult(polling_url, task_id)
    if result is not None and result.status == 'PENDING': 
        return True
    else:
        return False
        
#returns boolean value based on result=='SUCCESS' from celery table
def process_is_complete(polling_url=None, task_id=None):
    result = __get_asyncresult(polling_url, task_id)
    if result is not None and result.status == 'SUCCESS':
        return True
    else:
        return False
    
#returns result.result from celery table
def get_process_result(polling_url=None, task_id=None):
    result = __get_asyncresult(polling_url, task_id)
    if result is not None:
        return result.result
    else:
        return None
    
#get task_id from URLtoTaskID table
def get_taskid_from_url(polling_url):
    try:
        entry = URLtoTaskID.objects.get(url=polling_url)
        return entry.task_id
    except:
        #raise ValueError("Given URL does not map to any known task_id")
        return None
    
#get url from URLtoTaskID table    
def get_url_from_taskid(task_id):
    try:
        entry = URLtoTaskID.objects.get(task_id=task_id)
    except:
        raise ValueError("Given task_id does not map to any known URL")
    return entry.url

#get the AsyncResult object associated with the given (directly or indirectly) task_id
#(this object provides us access to the status field)
def __get_asyncresult(polling_url=None, task_id=None):
    if polling_url == task_id == None:
        raise ValueError("Either polling_url or task_id must be passed a value")
    if task_id is None:
        task_id = get_taskid_from_url(polling_url)
    from celery import result
    result = result.AsyncResult(task_id)
    if result.task_id == None:
        return None
    return result    
    

    