# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import print_function
import sys, time, datetime
from twisted.python import usage
from twisted.internet.defer import inlineCallbacks

from amptrac.client import connect, getRawAttachment, DEFAULT_AMP_ENDPOINT, Client

from twisted_tools import git

class ListOptions(usage.Options):

    def parseArgs(self, id):
        self['id'] = int(id)

class GetOptions(usage.Options):

    def parseArgs(self, id, filename=None):
        self['id'] = int(id)
        self['filename'] = filename

class ApplyOptions(usage.Options):

    optParameters = [['patch-level', 'p', '0', 'Patch level.']]

    def parseArgs(self, id, filename=None):
        self['id'] = int(id)


class Options(usage.Options):
    synopsis = "get-attachment [options] <ticket id>"

    optParameters = [['port', 'p', DEFAULT_AMP_ENDPOINT,
                      'Service description for the AMP connector.']]
    subCommands = [['list', '', ListOptions, 'List attachemts.'],
                   ['get', '', GetOptions, 'Get attachemt.'],
                   ['apply', '', ApplyOptions, 'Apply patch.']]

    def postOptions(self):
        self['id'] = self.subOptions['id']


def convertTime(unixtime):
    return datetime.datetime(*time.gmtime(unixtime)[:6])



def listAttachments(response):
    response['time'] = convertTime(response['time'])
    headline = "* #%(id)s - %(summary)s [%(status)s]\n" % response
    subline = ("`-- keywords: %(keywords)s reporter: %(reporter)s "
               "component: %(component)s\n" % response)

    attachments = []
    for item in response['attachments']:
        item['time'] = convertTime(item['time'])
        line = ('-- %(filename)s - %(author)s - %(time)s\n' % item)
        if item['description']:
            line += '   %(description)s\n' % item
        attachments.append(line)
    sys.__stdout__.write(''.join([headline, subline] + attachments))


def getLastAttachment(response):
    return getRawAttachment(response['id'], response['attachments'][-1]['filename'])

@inlineCallbacks
def applyPatch(patch, reactor, config, ticket):
    yield git.applyPatch(patch, config.subOptions['patch-level'], reactor=reactor)
    print(yield git.commit(
        'Apply %(filename)s from %(author)s.' % ticket['attachments'][-1],
        'Refs: #%(id)d' % ticket))


def main(reactor, *argv):
    config = Options()
    config.parseOptions(argv[1:])

    if config.subCommand == 'list':
        return (connect(reactor, config['port'])
                .addCallback(Client.fetchTicket, config['id'])
                .addCallback(listAttachments))
    elif config.subCommand == 'get':
        if config.subOptions['filename']:
            return (getRawAttachment(config.subOptions['id'], config.subOptions['filename'])
                    .addCallback(sys.__stdout__.write))
        else:
            return (connect(reactor, config['port'])
                    .addCallback(Client.fetchTicket, config['id'])
                    .addCallback(getLastAttachment)
                    .addCallback(sys.__stdout__.write))
    elif config.subCommand == 'apply':
        def apply(ticket):
            return (getLastAttachment(ticket)
                    .addCallback(applyPatch, reactor, config, ticket))
        return (connect(reactor, config['port'])
                .addCallback(Client.fetchTicket, config['id'])
                .addCallback(apply))
