#!/usr/bin/env python3
""" Run the gear: set up for and call command-line code """

import json
import os
import subprocess as sp
import sys

import flywheel
from utils import args
from utils.bids.download_bids import *
from utils.bids.validate_bids import *
from utils.fly.custom_log import *
from utils.fly.load_manifest_json import *
from utils.results.zip_output import *


def initialize(context):

    # Add manifest.json as the manifest_json attribute
    setattr(context, 'manifest_json', load_manifest_json())

    log = custom_log(context)

    context.log_config() # not configuring the log but logging the config

    # Instantiate custom gear dictionary to hold "gear global" info
    context.gear_dict = {}

    # the usual BIDS path:
    bids_path = os.path.join(context.work_dir, 'bids')
    context.gear_dict['bids_path'] = bids_path

    # Keep a list of errors to print all in one place at end
    context.gear_dict['errors'] = []

    # grab environment for gear
    with open('/tmp/gear_environ.json', 'r') as f:
        environ = json.load(f)
        context.gear_dict['environ'] = environ

        # Add environment to log if debugging
        kv = ''
        for k, v in environ.items():
            kv += k + '=' + v + ' '
        log.debug('Environment: ' + kv)

    return log


def create_command(context, log):

    # Create the command and validate the given arguments
    try:

        # editme: Set the actual gear command:
        command = ['fmriprep']

        # This should be done here in case there are nargs='*' arguments
        # These follow the BIDS Apps definition (https://github.com/BIDS-Apps)
        command.append(context.gear_dict['bids_path'])
        command.append(context.output_dir)
        command.append('participant')

        # Put command into gear_dict so arguments can be added in args.
        context.gear_dict['command'] = command

        # Process inputs, contextual values and build a dictionary of
        # key-value arguments specific for COMMAND
        args.get_inputs_and_args(context)

        # Validate the command parameter dictionary - make sure everything is 
        # ready to run so errors will appear before launching the actual gear 
        # code.  Raises Exception on fail
        args.validate(context)

        # Build final command-line (a list of strings)
        command = args.build_command(context)

    except Exception as e:
        context.gear_dict['errors'].append(e)
        log.critical(e,)
        log.exception('Error in creating and validating command.',)


def set_up_data(context, log):
    # Set up and validate data to be used by command
    try:

        # Download bids for the current session
        download_bids(context)

        # Validate Bids file heirarchy
        # Bids validation on a phantom tree may be occuring soon
        validate_bids(context)

    except Exception as e:
        context.gear_dict['errors'].append(e)
        log.critical(e,)
        log.exception('Error in BIDS download and validation.',)


def execute(context, log):
    try:

        log.info('Command: ' + ' '.join(context.gear_dict['command']))

        if not context.config['gear-dry-run']:

            # Run the actual command this gear was created for
            result = sp.run(context.gear_dict['command'], 
                        env=context.gear_dict['environ'],
                        stderr = sp.PIPE)

        else:
            result = sp.CompletedProcess
            result.returncode = 1
            result.stderr = 'gear-dry-run is set:  Did NOT run gear code.'

        log.info('Return code: ' + str(result.returncode))

        if result.returncode == 0:
            log.info('Command successfully executed!')

        else:
            log.error(result.stderr)
            log.info('Command failed.')

    except Exception as e:
        context.gear_dict['errors'].append(e)
        log.critical(e,)
        log.exception('Unable to execute command.')

    finally:

        # possibly save ALL intermediate output
        if context.config['gear-save-all-output']:
            zip_output(context)

        ret = result.returncode

        if len(context.gear_dict['errors']) > 0 :
            msg = 'Previous errors:\n'
            for err in context.gear_dict['errors']:
                msg += '  ' + str(type(err)).split("'")[1] + ': ' + str(err) + '\n'
            log.info(msg)
            ret = 1

        log.info('BIDS App Gear is done.')
        os.sys.exit(ret)
 

if __name__ == '__main__':

    context = flywheel.GearContext()

    log = initialize(context)

    create_command(context, log)

    set_up_data(context, log)

    execute(context, log)


# vi:set autoindent ts=4 sw=4 expandtab : See Vim, :help 'modeline'
