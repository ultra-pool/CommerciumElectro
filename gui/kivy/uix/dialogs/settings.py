from kivy.app import App
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.lang import Builder

from commerciumelectro.util import base_units
from commerciumelectro.i18n import languages
from commerciumelectro_gui.kivy.i18n import _
from commerciumelectro.plugins import run_hook
from commerciumelectro import coinchooser
from commerciumelectro.util import fee_levels

from .choice_dialog import ChoiceDialog

Builder.load_string('''
#:import partial functools.partial
#:import _ commerciumelectro_gui.kivy.i18n._
#:import VERSION commerciumelectro.version.ELECTRUM_VERSION

<SettingsDialog@Popup>
    id: settings
    title: _('CommerciumElectro Settings')
    disable_pin: False
    use_encryption: False
    BoxLayout:
        orientation: 'vertical'
        ScrollView:
            GridLayout:
                id: scrollviewlayout
                cols:1
                size_hint: 1, None
                height: self.minimum_height
                padding: '10dp'
                SettingsItem:
                    lang: settings.get_language_name()
                    title: 'LANGUAGE' + ': ' + str(self.lang)
                    description: _('Language')
                    action: partial(root.language_dialog, self)
                CardSeparator
                SettingsItem:
                    status: '' if root.disable_pin else ('ON' if root.use_encryption else 'OFF')
                    disabled: root.disable_pin
                    title: 'PIN code' + ': ' + self.status
                    description: _("Change your PIN code.")
                    action: partial(root.change_password, self)
                CardSeparator
                SettingsItem:
                    status: _('Yes') if app.use_change else _('No')
                    title: _('Use change addresses: Yes') if app.use_change else _('Use change addresses: No')
                    description: _("Send your change to separate addresses.")
                    message: 'Send excess coins to change addresses'
                    action: partial(root.boolean_dialog, 'use_change', 'Use change addresses', self.message)
                CardSeparator
                TopLabel:
                    text:_(' ')
                TopLabel:
                    text: _('Version')
                    font_name: "gui/kivy/data/fonts/SourceHanSansK-Bold.ttf"
                TopLabel
                    text: VERSION
                TopLabel:
                    text:_(' ')
                TopLabel:
                    text: _('Contact us') 
                    font_name: "gui/kivy/data/fonts/SourceHanSansK-Bold.ttf"
                    size_hint_x: 0.4
                TopLabel:
                    text: 'info@commercium.net'
                    size_hint_x: 0.8
                TopLabel:
                    text: _(' ')
                TopLabel:
                    text: _('Homepage') 
                    font_name: "gui/kivy/data/fonts/SourceHanSansK-Bold.ttf"
                    size_hint_x: 0.4
                TopLabel:
                    markup: True
                    text: '[color=6666ff][ref=x]https://www.commercium.net[/ref][/color]'
                    size_hint_x: 0.8
                    on_ref_press:
                        import webbrowser
                        webbrowser.open("https://www.commercium.net")
                TopLabel:
                    text: _(' ')
                CardSeparator

''')
# Builder.load_file('gui/kivy/uix/dialog/dialog_kv/settings.kv')


class SettingsDialog(Factory.Popup):

    def __init__(self, app):
        self.app = app
        self.plugins = self.app.plugins
        self.config = self.app.electrum_config
        Factory.Popup.__init__(self)
        layout = self.ids.scrollviewlayout
        layout.bind(minimum_height=layout.setter('height'))
        # cached dialogs
        self._fx_dialog = None
        self._fee_dialog = None
        self._proxy_dialog = None
        self._language_dialog = None
        self._unit_dialog = None
        self._coinselect_dialog = None

    def update(self):
        self.wallet = self.app.wallet
        self.disable_pin = self.wallet.is_watching_only() if self.wallet else True
        self.use_encryption = self.wallet.has_password() if self.wallet else False

    def get_language_name(self):
        return languages.get(self.config.get('language', 'zh_CN'), '')

    def change_password(self, item, dt):
        self.app.change_password(self.update)

    def language_dialog(self, item, dt):
        if self._language_dialog is None:
            l = self.config.get('language', 'zh_CN')
            def cb(key):
                self.config.set_key("language", key, True)
                item.lang = self.get_language_name()
                self.app.language = key
                self.app._trigger_update_status()
            self._language_dialog = ChoiceDialog(_('Language'), languages, l, cb)
        self._language_dialog.open()

    def unit_dialog(self, item, dt):
        if self._unit_dialog is None:
            def cb(text):
                self.app._set_bu(text)
                item.bu = self.app.base_unit
            self._unit_dialog = ChoiceDialog(_('Denomination'), list(base_units.keys()), self.app.base_unit, cb)
        self._unit_dialog.open()

    def coinselect_status(self):
        return coinchooser.get_name(self.app.electrum_config)

    def coinselect_dialog(self, item, dt):
        if self._coinselect_dialog is None:
            choosers = sorted(coinchooser.COIN_CHOOSERS.keys())
            chooser_name = coinchooser.get_name(self.config)
            def cb(text):
                self.config.set_key('coin_chooser', text)
                item.status = text
            self._coinselect_dialog = ChoiceDialog(_('Coin selection'), choosers, chooser_name, cb)
        self._coinselect_dialog.open()

    def proxy_status(self):
        server, port, protocol, proxy, auto_connect = self.app.network.get_parameters()
        return proxy.get('host') +':' + proxy.get('port') if proxy else _('None')

    def proxy_dialog(self, item, dt):
        if self._proxy_dialog is None:
            server, port, protocol, proxy, auto_connect = self.app.network.get_parameters()
            def callback(popup):
                if popup.ids.mode.text != 'None':
                    proxy = {
                        'mode':popup.ids.mode.text,
                        'host':popup.ids.host.text,
                        'port':popup.ids.port.text,
                        'user':popup.ids.user.text,
                        'password':popup.ids.password.text
                    }
                else:
                    proxy = None
                self.app.network.set_parameters(server, port, protocol, proxy, auto_connect)
                item.status = self.proxy_status()
            popup = Builder.load_file('gui/kivy/uix/ui_screens/proxy.kv')
            popup.ids.mode.text = proxy.get('mode') if proxy else 'None'
            popup.ids.host.text = proxy.get('host') if proxy else ''
            popup.ids.port.text = proxy.get('port') if proxy else ''
            popup.ids.user.text = proxy.get('user') if proxy else ''
            popup.ids.password.text = proxy.get('password') if proxy else ''
            popup.on_dismiss = lambda: callback(popup)
            self._proxy_dialog = popup
        self._proxy_dialog.open()

    def plugin_dialog(self, name, label, dt):
        from .checkbox_dialog import CheckBoxDialog
        def callback(status):
            self.plugins.enable(name) if status else self.plugins.disable(name)
            label.status = 'ON' if status else 'OFF'
        status = bool(self.plugins.get(name))
        dd = self.plugins.descriptions.get(name)
        descr = dd.get('description')
        fullname = dd.get('fullname')
        d = CheckBoxDialog(fullname, descr, status, callback)
        d.open()

    def fee_status(self):
        if self.config.get('dynamic_fees', True):
            return fee_levels[self.config.get('fee_level', 2)]
        else:
            return self.app.format_amount_and_units(self.config.fee_per_kb()) + '/kB'

    def fee_dialog(self, label, dt):
        if self._fee_dialog is None:
            from .fee_dialog import FeeDialog
            def cb():
                label.status = self.fee_status()
            self._fee_dialog = FeeDialog(self.app, self.config, cb)
        self._fee_dialog.open()

    def boolean_dialog(self, name, title, message, dt):
        from .checkbox_dialog import CheckBoxDialog
        CheckBoxDialog(_(title), _(message), getattr(self.app, name), lambda x: setattr(self.app, name, x)).open()

    def fx_status(self):
        fx = self.app.fx
        if fx.is_enabled():
            source = fx.exchange.name()
            ccy = fx.get_currency()
            return '%s [%s]' %(ccy, source)
        else:
            return _('None')

    def fx_dialog(self, label, dt):
        if self._fx_dialog is None:
            from .fx_dialog import FxDialog
            def cb():
                label.status = self.fx_status()
            self._fx_dialog = FxDialog(self.app, self.plugins, self.config, cb)
        self._fx_dialog.open()
