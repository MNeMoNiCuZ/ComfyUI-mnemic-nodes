import functools

current_prompt = {}
current_extra_data = {}
prompt_executer = None
current_save_node_id = None
_installed = False


def _prefix_function(function, prefunction):
    @functools.wraps(function)
    def run(*args, **kwargs):
        prefunction(*args, **kwargs)
        return function(*args, **kwargs)
    return run


def _pre_execute(self, prompt, prompt_id, extra_data, execute_outputs):
    global current_prompt, current_extra_data, prompt_executer
    current_prompt = prompt
    current_extra_data = extra_data
    prompt_executer = self


def _make_pre_get_input_data(target_class_name: str):
    def _pre_get_input_data(inputs, class_def, unique_id, *args, **kwargs):
        global current_save_node_id
        try:
            cls_name = getattr(class_def, "__name__", "")
            if cls_name == target_class_name:
                current_save_node_id = str(unique_id)
        except Exception:
            pass
    return _pre_get_input_data


def install_runtime_hooks(target_class_name: str = "ImageSaveWithMetadata"):
    global _installed
    if _installed:
        return

    import execution

    execution.PromptExecutor.execute = _prefix_function(execution.PromptExecutor.execute, _pre_execute)
    execution.get_input_data = _prefix_function(execution.get_input_data, _make_pre_get_input_data(target_class_name))

    # mirror source-node compatibility shim for execution list caches
    try:
        from comfy_execution.graph import ExecutionList

        def _exec_list_get_output_cache(self, input_unique_id, unique_id):
            return self.output_cache.get(input_unique_id)

        if not hasattr(ExecutionList, "get_output_cache"):
            ExecutionList.get_output_cache = _exec_list_get_output_cache
    except Exception:
        pass

    # compatibility shim for cache objects used by execution.get_input_data
    try:
        from comfy_execution.caching import HierarchicalCache, LRUCache, NullCache

        def _cache_get_cache(self, input_unique_id, unique_id):
            try:
                return self.get_local(input_unique_id)
            except Exception:
                return None

        def _null_get_cache(self, input_unique_id, unique_id):
            return None

        if not hasattr(HierarchicalCache, "get_cache"):
            HierarchicalCache.get_cache = _cache_get_cache
        if not hasattr(LRUCache, "get_cache"):
            LRUCache.get_cache = _cache_get_cache
        if not hasattr(NullCache, "get_cache"):
            NullCache.get_cache = _null_get_cache

        # some versions call get_output_cache instead of get_cache
        if not hasattr(HierarchicalCache, "get_output_cache"):
            HierarchicalCache.get_output_cache = _cache_get_cache
        if not hasattr(LRUCache, "get_output_cache"):
            LRUCache.get_output_cache = _cache_get_cache
        if not hasattr(NullCache, "get_output_cache"):
            NullCache.get_output_cache = _null_get_cache
    except Exception:
        pass

    _installed = True
