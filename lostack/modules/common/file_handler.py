"""Handler for file editing requests, easily extended"""

import yaml
from flask import jsonify, render_template

class FileHandler:
    """
    File Read/Write handler
    Will expand to other files as the editor becomes more advanced
    """
    
    @staticmethod
    def handle_yaml_edit(filepath, filename, request):
        """Consolidated YAML file editing logic"""
        if request.method == 'POST':
            content = request.form['filecontent']
            
            # Validate YAML
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                return jsonify({
                    'success': False,
                    'message': f'Invalid YAML format: {str(e)}'
                }), 400
            
            # Save file
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
                return jsonify({'success': True, 'message': 'File saved successfully'})
            except IOError as e:
                return jsonify({
                    'success': False,
                    'message': f'Error saving file: {str(e)}'
                }), 500
        
        # GET request - load file
        try:
            with open(filepath) as f:
                file_content = f.read()
            return render_template('editor.html', filename=filename, filecontent=file_content)
        except IOError as e:
            return jsonify({
                'success': False,
                'message': f'Error reading file: {str(e)}'
            }), 500

    # TODO: Add env editor