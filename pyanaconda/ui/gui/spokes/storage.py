# Storage configuration spoke classes
#
# Copyright (C) 2011, 2012  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): David Lehman <dlehman@redhat.com>
#

"""
    TODO:

        - add button within sw_needs text in options dialogs 2,3
        - udev data gathering
            - udev fwraid, mpath would sure be nice
        - status/completed
            - what are noteworthy status events?
                - disks selected
                    - exclusiveDisks non-empty
                - sufficient space for software selection
                - autopart selected
                - custom selected
                    - performing custom configuration
                - storage configuration complete
        - spacing and border width always 6

"""

from gi.repository import Gdk, Gtk
from gi.repository import AnacondaWidgets

from pyanaconda.ui.gui import UIObject, communication
from pyanaconda.ui.gui.spokes import NormalSpoke
from pyanaconda.ui.gui.spokes.lib.cart import SelectedDisksDialog
from pyanaconda.ui.gui.categories.storage import StorageCategory
from pyanaconda.ui.gui.utils import enlightbox, gdk_threaded

from pyanaconda.storage.size import Size
from pyanaconda.product import productName
from pyanaconda.flags import flags

from pykickstart.constants import *

import gettext

_ = lambda x: gettext.ldgettext("anaconda", x)
N_ = lambda x: x
P_ = lambda x, y, z: gettext.ldngettext("anaconda", x, y, z)

__all__ = ["StorageSpoke"]

class FakeDiskLabel(object):
    def __init__(self, free=0):
        self.free = free

class FakeDisk(object):
    def __init__(self, name, size=0, free=0, partitioned=True, vendor=None,
                 model=None, serial=None, removable=False):
        self.name = name
        self.size = size
        self.format = FakeDiskLabel(free=free)
        self.partitioned = partitioned
        self.vendor = vendor
        self.model = model
        self.serial = serial
        self.removable = removable

    @property
    def description(self):
        return "%s %s" % (self.vendor, self.model)

def getDisks(devicetree, fake=False):
    if not fake:
        disks = [d for d in devicetree.devices if d.isDisk and
                                                  not d.format.hidden and
                                                  not (d.protected and
                                                       d.removable)]
    else:
        disks = []
        disks.append(FakeDisk("sda", size=300000, free=10000, serial="00001",
                              vendor="Seagate", model="Monster"))
        disks.append(FakeDisk("sdb", size=300000, free=300000, serial="00002",
                              vendor="Seagate", model="Monster"))
        disks.append(FakeDisk("sdc", size=8000, free=2100, removable=True,
                              vendor="SanDisk", model="Cruzer", serial="00003"))

    return disks

def size_str(mb):
    if isinstance(mb, Size):
        spec = str(mb)
    else:
        spec = "%s mb" % mb

    return str(Size(spec=spec)).upper()

class InstallOptions1Dialog(UIObject):
    builderObjects = ["options1_dialog"]
    mainWidgetName = "options1_dialog"
    uiFile = "spokes/storage.ui"

    RESPONSE_CANCEL = 0
    RESPONSE_CONTINUE = 1
    RESPONSE_MODIFY_SW = 2
    RESPONSE_RECLAIM = 3
    RESPONSE_QUIT = 4

    def run(self):
        rc = self.window.run()
        self.window.destroy()
        return rc

    def refresh(self, required_space, disk_free, fs_free, autopart):
        self.custom = not autopart
        self.custom_checkbutton = self.builder.get_object("options1_custom_check")
        self.custom_checkbutton.set_active(self.custom)

        options_label = self.builder.get_object("options1_label")

        options_text = (_("You have plenty of space to install <b>%s</b>, so "
                          "we can automatically\n"
                          "configure the rest of the installation for you.\n\n"
                          "You're all set!")
                        % productName)
        options_label.set_markup(options_text)

    def _set_free_space_labels(self, disk_free, fs_free):
        disk_free_text = size_str(disk_free)
        self.disk_free_label.set_text(disk_free_text)

        fs_free_text = size_str(fs_free)
        self.fs_free_label.set_text(fs_free_text)

    def _get_sw_needs_text(self, required_space):
        required_space_text = size_str(required_space)
        sw_text = (_("Your current <b>%s</b> software selection requires "
                      "<b>%s</b> of available space.")
                   % (productName, required_space_text))
        return sw_text

    # signal handlers
    def on_cancel_clicked(self, button):
        # return to the spoke without making any changes
        print "CANCEL CLICKED"

    def on_quit_clicked(self, button):
        print "QUIT CLICKED"

    def on_modify_sw_clicked(self, button):
        # switch to the software selection hub
        print "MODIFY SOFTWARE CLICKED"

    def on_reclaim_clicked(self, button):
        # show reclaim screen/dialog
        print "RECLAIM CLICKED"

    def on_continue_clicked(self, button):
        print "CONTINUE CLICKED"

    def on_custom_toggled(self, checkbutton):
        self.custom = checkbutton.get_active()

class InstallOptions2Dialog(InstallOptions1Dialog):
    builderObjects = ["options2_dialog"]
    mainWidgetName = "options2_dialog"

    def refresh(self, required_space, disk_free, fs_free, autopart):
        self.custom = not autopart
        self.custom_checkbutton = self.builder.get_object("options2_custom_check")
        self.custom_checkbutton.set_active(self.custom)

        sw_text = self._get_sw_needs_text(required_space)
        label_text = _("%s\nThe disks you've selected have the following "
                       "amounts of free space:") % sw_text
        self.builder.get_object("options2_label1").set_markup(label_text)

        self.disk_free_label = self.builder.get_object("options2_disk_free_label")
        self.fs_free_label = self.builder.get_object("options2_fs_free_label")
        self._set_free_space_labels(disk_free, fs_free)

        label_text = (_("<b>You don't have enough space available to install "
                        "%s</b>, but we can help you\n"
                        "reclaim space by shrinking or removing existing partitions.")
                      % productName)
        self.builder.get_object("options2_label2").set_markup(label_text)

    def on_custom_toggled(self, checkbutton):
        super(InstallOptions2Dialog, self).on_custom_toggled(checkbutton)
        self.builder.get_object("options2_cancel_button").set_sensitive(not self.custom)
        self.builder.get_object("options2_modify_sw_button").set_sensitive(not self.custom)

class InstallOptions3Dialog(InstallOptions1Dialog):
    builderObjects = ["options3_dialog"]
    mainWidgetName = "options3_dialog"

    def refresh(self, required_space, disk_free, fs_free, autopart):
        self.custom = not autopart
        sw_text = self._get_sw_needs_text(required_space)
        label_text = (_("%s\nYou don't have enough space available to install "
                        "<b>%s</b>, even if you used all of the free space\n"
                        "available on the selected disks.")
                      % (sw_text, productName))
        self.builder.get_object("options3_label1").set_markup(label_text)

        self.disk_free_label = self.builder.get_object("options3_disk_free_label")
        self.fs_free_label = self.builder.get_object("options3_fs_free_label")
        self._set_free_space_labels(disk_free, fs_free)

        label_text = _("<b>You don't have enough space available to install "
                       "%s</b>, even if you used all of the free space\n"
                       "available on the selected disks.  You could add more "
                       "disks for additional space,\n"
                       "modify your software selection to install a smaller "
                       "version of <b>%s</b>, or quit the installer.") % (productName, productName)
        self.builder.get_object("options3_label2").set_markup(label_text)

class StorageSpoke(NormalSpoke):
    builderObjects = ["storageWindow"]
    mainWidgetName = "storageWindow"
    uiFile = "spokes/storage.ui"

    category = StorageCategory

    # other candidates: computer-symbolic, folder-symbolic
    icon = "drive-harddisk-symbolic"
    title = N_("INSTALLATION DESTINATION")

    def __init__(self, *args, **kwargs):
        NormalSpoke.__init__(self, *args, **kwargs)
        self._ready = False
        self.selected_disks = self.data.clearpart.drives[:]

        if not flags.automatedInstall:
            # default to using autopart for interactive installs
            self.data.autopart.autopart = True

        self.autopart = self.data.autopart.autopart

        # FIXME:  This needs to be set to a real value via some TBD UI.
        self.clearPartType = CLEARPART_TYPE_LINUX

    def apply(self):
        self.data.clearpart.drives = self.selected_disks[:]
        self.data.autopart.autopart = self.autopart

        # no thanks, lvm
        self.data.autopart.type = AUTOPART_TYPE_PLAIN

        if self.autopart:
            self.clearPartType = CLEARPART_TYPE_ALL
        else:
            self.clearPartType = CLEARPART_TYPE_NONE

        self.data.bootloader.location = "mbr"

        self.data.clearpart.type = self.clearPartType

        if self.autopart:
            self.data.clearpart.execute(self.storage, self.data, self.instclass)

        # Pick the first disk to be the destination device for the bootloader.
        # This appears to be the minimum amount of configuration required to
        # make autopart happy with the bootloader settings.
        if not self.data.bootloader.bootDrive:
            self.data.bootloader.bootDrive = self.storage.bootloader.disks[0].name

        self.data.bootloader.execute(self.storage, self.data, self.instclass)

        # this won't do anything if autopart is not selected
        self.data.autopart.execute(self.storage, self.data, self.instclass)

    @property
    def completed(self):
        return self.status != _("No disks selected")

    @property
    def ready(self):
        # By default, the storage spoke is not ready.  We have to wait until
        # storageInitialize is done.
        return self._ready

    @property
    def status(self):
        """ A short string describing the current status of storage setup. """
        msg = _("No disks selected")
        if self.data.clearpart.drives:
            msg = P_(("%d disk selected"),
                     ("%d disks selected"),
                     len(self.data.clearpart.drives)) % len(self.data.clearpart.drives)

            if self.data.autopart.autopart:
                msg = _("Automatic partitioning selected")

                # if we had a storage instance we could check for a defined root

        return msg

    def _on_disk_clicked(self, overview, event):
        print "DISK CLICKED: %s" % overview.get_property("popup-info").partition("|")[0].strip()

        # This handler only runs for these two kinds of events, and only for
        # activate-type keys (space, enter) in the latter event's case.
        if not event.type in [Gdk.EventType.BUTTON_PRESS, Gdk.EventType.KEY_RELEASE]:
            return

        if event.type == Gdk.EventType.KEY_RELEASE and \
           event.keyval not in [Gdk.KEY_space, Gdk.KEY_Return, Gdk.KEY_ISO_Enter, Gdk.KEY_KP_Enter, Gdk.KEY_KP_Space]:
              return

        self._update_disk_list()
        self._update_summary()

    def refresh(self):
        # synchronize our local data store with the global ksdata
        self.selected_disks = self.data.clearpart.drives[:]
        self.autopart = self.data.autopart.autopart

        # update the selections in the ui
        overviews = self.local_disks_box.get_children()
        for overview in overviews:
            name = overview.get_property("popup-info").partition("|")[0].strip()
            overview.set_chosen(name in self.selected_disks)

        self._update_summary()

    def initialize(self):
        from pyanaconda.threads import threadMgr, AnacondaThread
        from pyanaconda.ui.gui.utils import setViewportBackground

        NormalSpoke.initialize(self)

        summary_label = self.builder.get_object("summary_button").get_children()[0]
        summary_label.set_use_markup(True)

        self.local_disks_box = self.builder.get_object("local_disks_box")
        #specialized_disks_box = self.builder.get_object("specialized_disks_box")

        viewport = self.builder.get_object("localViewport")
        setViewportBackground(viewport)

        threadMgr.add(AnacondaThread(name="AnaStorageWatcher", target=self._initialize))

    def _initialize(self):
        from pyanaconda.threads import threadMgr

        communication.send_message(self.__class__.__name__, _("Probing storage..."))

        storageThread = threadMgr.get("AnaStorageThread")
        if storageThread:
            storageThread.join()

        print self.data.clearpart.drives

        self.disks = getDisks(self.storage.devicetree)

        with gdk_threaded():
            # properties: kind, description, capacity, os, popup-info
            for disk in self.disks:
                if disk.removable:
                    kind = "drive-removable-media"
                else:
                    kind = "drive-harddisk"

                size = size_str(disk.size)
                popup_info = "%s | %s" % (disk.name, disk.serial)
                overview = AnacondaWidgets.DiskOverview(disk.description,
                                                        kind,
                                                        size,
                                                        popup=popup_info)
                self.local_disks_box.pack_start(overview, False, False, 0)

                # FIXME: this will need to get smarter
                #
                # maybe a little function that resolves each item in onlyuse using
                # udev_resolve_devspec and compares that to the DiskDevice?
                overview.set_chosen(disk.name in self.selected_disks)
                overview.connect("button-press-event", self._on_disk_clicked)
                overview.connect("key-release-event", self._on_disk_clicked)
                overview.show_all()

            self._update_summary()

        self._ready = True
        communication.send_ready(self.__class__.__name__)

    def _update_summary(self):
        """ Update the summary based on the UI. """
        print "UPDATING SUMMARY"
        count = 0
        capacity = 0
        free = Size(bytes=0)

        free_space = self.storage.getFreeSpace(clearPartType=self.clearPartType)
        selected = [d for d in self.disks if d.name in self.selected_disks]

        for disk in selected:
            capacity += disk.size
            free += free_space[disk.name][0]
            count += 1

        summary = (P_(("%d disk selected; %s capacity; %s free ..."),
                      ("%d disks selected; %s capacity; %s free ..."),
                      count) % (count, str(Size(spec="%s MB" % capacity)), free))
        markup = "<span foreground='blue'><u>%s</u></span>" % summary
        summary_label = self.builder.get_object("summary_button").get_children()[0]
        summary_label.set_markup(markup)

        if count == 0:
            self.window.set_info(Gtk.MessageType.WARNING, _("No disks selected; please select at least one disk to install to."))
        else:
            self.window.clear_info()

        self.builder.get_object("continue_button").set_sensitive(count > 0)
        self.builder.get_object("summary_button").set_sensitive(count > 0)

    def _update_disk_list(self):
        """ Update self.selected_disks based on the UI. """
        print "UPDATING DISK LIST"
        overviews = self.local_disks_box.get_children()
        for overview in overviews:
            name = overview.get_property("popup-info").partition("|")[0].strip()

            selected = overview.get_chosen()
            if selected and name not in self.selected_disks:
                self.selected_disks.append(name)

            if not selected and name in self.selected_disks:
                self.selected_disks.remove(name)

    # signal handlers
    def on_summary_clicked(self, button):
        # show the selected disks dialog
        dialog = SelectedDisksDialog(self.data)
        dialog.refresh([d for d in self.disks if d.name in self.selected_disks])
        rc = self.run_lightbox_dialog(dialog)
        # update selected disks since some may have been removed
        self.selected_disks = [d.name for d in dialog.disks]

        # update the UI to reflect changes to self.selected_disks
        overviews = self.local_disks_box.get_children()
        for overview in overviews:
            name = overview.get_property("popup-info").partition("|")[0].strip()

            overview.set_chosen(name in self.selected_disks)
        self._update_summary()

    def run_lightbox_dialog(self, dialog):
        with enlightbox(self.window, dialog.window):
            rc = dialog.run()

        return rc

    def on_continue_clicked(self, button):
        # show the installation options dialog
        disks = [d for d in self.disks if d.name in self.selected_disks]
        free_space = self.storage.getFreeSpace(disks=disks,
                                               clearPartType=self.clearPartType)
        disk_free = sum([f[0] for f in free_space.itervalues()])
        fs_free = sum([f[1] for f in free_space.itervalues()])
        required_space = self.payload.spaceRequired
        if disk_free >= required_space:
            dialog = InstallOptions1Dialog(self.data)
        elif sum([d.size for d in disks]) >= required_space:
            dialog = InstallOptions2Dialog(self.data)
        else:
            dialog = InstallOptions3Dialog(self.data)

        dialog.refresh(required_space, disk_free, fs_free, self.autopart)
        rc = self.run_lightbox_dialog(dialog)
        if rc == dialog.RESPONSE_CONTINUE:
            # depending on custom/autopart, either set up autopart or show
            # custom partitioning ui
            self.autopart = not dialog.custom
            if dialog.custom:
                self.skipTo = "CustomPartitioningSpoke"

            self.on_back_clicked(self.window)
        elif rc == dialog.RESPONSE_CANCEL:
            # stay on this spoke
            print "user chose to continue disk selection"
        elif rc == dialog.RESPONSE_MODIFY_SW:
            # go to software spoke
            print "user chose to modify software selection"
        elif rc == dialog.RESPONSE_RECLAIM:
            if dialog.custom:
                self.skipTo = "CustomPartitioningSpoke"
            else:
                # go to tug-of-war
                pass

            self.on_back_clicked(self.window)
        elif rc == dialog.RESPONSE_QUIT:
            raise SystemExit("user-selected exit")

    def on_add_disk_clicked(self, button):
        print "ADD DISK CLICKED"