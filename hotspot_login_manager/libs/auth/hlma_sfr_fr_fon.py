# -*- coding:utf-8 -*-
#
# hotspot-login-manager
# https://github.com/syam44/Hotspot-Login-Manager
#
# Distributed under the GNU General Public License version 3
# https://www.gnu.org/copyleft/gpl.html
#
# Authors: syam (aks92@free.fr)
#
# Description: Authentication plugin for SFR.FR + FON hotspots
#
# Thanks a lot to:
# - jarlax from debian-fr.org who pointed out some Python3.2 bugs
# - MCMic from debian-fr.org who helped debug the hotspot.wifi.sfr.fr case
#


#-----------------------------------------------------------------------------
import re
import urllib.parse
#
from hotspot_login_manager.libs.daemon import hlm_auth_plugins
from hotspot_login_manager.libs.daemon import hlm_http


#-----------------------------------------------------------------------------
def getSupportedProviders():
    # See daemon/hlm_auth_plugins
    return { 'sfr.fr': ['SFR WiFi FON', 'SFR WiFi Public', 'Neuf WiFi FON', 'Neuf WiFi Public'],
             'fon': ['SFR WiFi FON', 'Neuf WiFi FON'],
           }


#-----------------------------------------------------------------------------
def getSupportedRedirectPrefixes():
    return ['https://hotspot.neuf.fr/indexEncryptingChilli.php?',
            'https://hotspot.wifi.sfr.fr/indexEncryptingChilli.php?']


#-----------------------------------------------------------------------------
def authenticate(redirectURL, connectedSSIDs):

    debugMessageHeader = 'AuthPlugin {0}'.format(quote(pluginName))
    def debugMessage(message, *args):
        if args != tuple():
            message = message.format(*args)
        message = '{0}: {1}'.format(debugMessageHeader, message)
        return message


    def reportFailure(message, *args):
        message = debugMessage('[FAILURE] ' + message, *args)
        raise hlm_auth_plugins.Status_Error(pluginName, message)

    match = _regexDomainRedirect.search(redirectURL)
    if match == None:
        reportFailure('hotspot domain name is missing.')
    domainRedirect = match.group(1)
    if __DEBUG__: logDebug(debugMessage('domainRedirect is {0}'.format(domainRedirect)))
    regexChilliURL = re.compile('SFRLoginURL_JIL=(https://{0}/indexEncryptingChilli.php?[^>]+)-->'.format(re.escape(domainRedirect)))

    # Extract the URL arguments
    try:
        urlArgs = hlm_http.splitUrlArguments(redirectURL, ['challenge', 'mode', 'uamip', 'uamport', 'channel'], 'redirect URL')
        if __DEBUG__: logDebug(debugMessage('got all required arguments from the redirect URL.'))
    except BaseException as exc:
        reportFailure(exc)

    # Get the login page
    try:
        result = hlm_http.urlOpener().open(redirectURL, timeout = 10)
        pageData = hlm_http.readAll(result)
        if not (type(pageData) is str):
          pageData = str(pageData, 'utf-8')
        result.close()
        if __DEBUG__: logDebug(debugMessage('grabbed the login webpage.'))
    except hlm_http.CertificateError as exc:
        raise
    except BaseException as exc:
        reportFailure('error while grabbing the login webpage: {0}'.format(exc))

    # Basic check to see if we actually are on a SFR "NeufBox"
    if _regexCheckNB4.search(pageData) == None:
        reportFailure('this is not a "NeufBox4".')
    if __DEBUG__: logDebug(debugMessage('seems we have a "NeufBox".'))

    # Is the hotspot FON-enabled?
    hasFONsupport = (_regexCheckChoiceFON.search(pageData) != None)
    if __DEBUG__:
        if hasFONsupport:
            logDebug(debugMessage('we have FON support.'))
        else:
            logDebug(debugMessage('we don\'t have FON support.'))

    # Double-check the Chillispot URL
    match = regexChilliURL.search(pageData)
    if match == None:
        reportFailure('in-page data is missing.')
    if match.group(1) != redirectURL:
        reportFailure('in-page data conflicts with the redirected URL.')
    if __DEBUG__: logDebug(debugMessage('in-page data confirms the redirect URL.'))

    # Prepare data that is dependent on the kind of hotspot / configured credentials
    if 'sfr.fr' in pluginCredentials:
        hotspotCredentials = 'sfr.fr'
        hotspotAccessType = 'neuf'
        if hasFONsupport:
            hotspotChoice = 'choix=neuf&'
        else:
            hotspotChoice = ''
    elif hasFONsupport and ('fon' in pluginCredentials):
        hotspotCredentials = 'fon'
        hotspotAccessType = 'fon'
        hotspotChoice = 'choix=fon&'
    else:
        reportFailure('this plugin only supports «sfr.fr» and «fon» credentials.')

    if __DEBUG__: logDebug(debugMessage('using {0} credentials'.format(quote(hotspotCredentials))))
    debugMessageHeader = 'AuthPlugin {0} (credentials {1})'.format(quote(pluginName), quote(hotspotCredentials))

    (user, password) = pluginCredentials[hotspotCredentials]
    postData = hotspotChoice + 'username={0}&password={1}&conditions=on&challenge={2}&accessType={7}&lang=fr&mode={3}&userurl=http%253a%252f%252fwww.google.com%252f&uamip={4}&uamport={5}&channel={6}&connexion=Connexion'.format(urllib.parse.quote(user), urllib.parse.quote(password), urlArgs['challenge'], urlArgs['mode'], urlArgs['uamip'], urlArgs['uamport'], urlArgs['channel'], hotspotAccessType)

    # Ask the hotspot gateway to give us the Chillispot URL
    try:
        # FIXME Python 3.2 (postData)
        result = hlm_http.urlOpener().open('https://{0}/nb4_crypt.php'.format(domainRedirect), data = postData, timeout = 10)
        pageData = hlm_http.readAll(result)
        if not (type(pageData) is str):
          pageData = str(pageData, 'utf-8')
        result.close()
        if __DEBUG__: logDebug(debugMessage('grabbed the encryption gateway (JS redirect) result webpage.'))
    except hlm_http.CertificateError as exc:
        raise
    except BaseException as exc:
        reportFailure('error while grabbing the encryption gateway (JS redirect) result webpage: {0}'.format(exc))

    # OK, now we have to put up with a Javascript redirect. I mean, WTF?
    match = _regexJSRedirect.search(pageData)
    if match == None:
        reportFailure('missing URL in the encryption gateway (JS redirect) result webpage.')
    redirectURL = match.group(1)
    # Let's see what Chillispot will answer us...
    redirectURL = hlm_http.detectRedirect(redirectURL)
    if redirectURL == None:
        reportFailure('something went wrong during the Chillispot query (redirect expected, but none obtained).')

    # Check the final URL arguments
    try:
        urlArgs = hlm_http.splitUrlArguments(redirectURL, ['res'], 'redirect URL')
        urlArgs = urlArgs['res'].lower()
    except BaseException as exc:
        reportFailure(exc)

    if urlArgs == 'failed':
        raise hlm_auth_plugins.Status_WrongCredentials(pluginName, hotspotCredentials)

    if (urlArgs != 'success') and (urlArgs != 'already'):
        reportFailure('Chillispot didn\'t let us log in, no idea why. Here\'s the redirected URL: {0}'.format(redirectURL))

    raise hlm_auth_plugins.Status_Success(pluginName, hotspotCredentials)


#-----------------------------------------------------------------------------
#
# Pre-compiled regular expressions for authenticate()
#
_regexDomainRedirect = re.compile('https://([^/]+)/')
_regexCheckNB4 = re.compile('<form action="nb4_crypt\\.php" ')
_regexCheckChoiceFON = re.compile('<select name="choix" id="choix">[^<]+<option value="neuf" selected>SFR</option>[^<]+<option value="fon">Fonero</option>')
_regexJSRedirect = re.compile('window.location = "([^"]+)";')


#-----------------------------------------------------------------------------
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
