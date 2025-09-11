"""Creates streams used to pipe data through a websocket"""

import time
import logging
from flask import Response
from .stream_generator import stream_generator

class StreamHandler:
    """Handler for websocket stream generation"""
    
    @staticmethod
    def create_response(generator_func, mimetype='text/event-stream'):
        """Standard response wrapper for all streaming endpoints"""
        return Response(
            generator_func(),
            mimetype=mimetype,
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
    
    @staticmethod
    def generic_stream(action, target, *args, force_sync=True, **kw):
        """Generic streaming handler"""
        
        stream = stream_generator(action, (target, *args), kw)
        
        def generator():
            for message in stream(): 
                yield message
            if force_sync:
                try:
                    from ..package_manager import get_docker_handler
                    get_docker_handler().force_sync()
                except Exception as e:
                    yield(f"Error Handling sync - {e}")
                    time.sleep(1)
                
        return StreamHandler.create_response(generator)

    @staticmethod
    def message_completion_stream(message, force_sync=False):
        """
        Stream a message and complete the stream
        """
        def generator():
            yield message
            
            yield "__COMPLETE__"
            
            if force_sync:
                from ..package_manager import get_docker_handler
                get_docker_handler().force_sync()
                
        return StreamHandler.create_response(generator)