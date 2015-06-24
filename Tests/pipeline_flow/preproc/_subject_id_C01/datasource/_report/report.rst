Node: datasource (io)
=====================

 Hierarchy : preproc.datasource
 Exec ID : datasource.a0

Original Inputs
---------------

* base_directory : /data1/projects/nipype/tf/tka_nipype/Tests/pipeline_flow/data/
* field_template : {'pet': 'PET/test_%s_pet.mnc', 'mri': 'CIVET/test_%s_mri.mnc'}
* ignore_exception : False
* raise_on_empty : True
* sort_filelist : False
* study_prefix : test
* subject_id : C01
* template : *
* template_args : {'pet': [['subject_id']], 'mri': [['subject_id']]}

Execution Inputs
----------------

* base_directory : /data1/projects/nipype/tf/tka_nipype/Tests/pipeline_flow/data/
* field_template : {'pet': 'PET/test_%s_pet.mnc', 'mri': 'CIVET/test_%s_mri.mnc'}
* ignore_exception : False
* raise_on_empty : True
* sort_filelist : False
* study_prefix : test
* subject_id : C01
* template : *
* template_args : {'pet': [['subject_id']], 'mri': [['subject_id']]}

Execution Outputs
-----------------

* mri : <undefined>
* pet : /data1/projects/nipype/tf/tka_nipype/Tests/pipeline_flow/data/PET/test_C01_pet.mnc

Runtime info
------------

* duration : 0.00238
* hostname : ace-ws-30

Environment
~~~~~~~~~~~

* COLORTERM : gnome-terminal
* DBUS_SESSION_BUS_ADDRESS : unix:abstract=/tmp/dbus-61wgQoQac1,guid=35996c42ae8c3d9dae01d31100000015
* DEFAULTS_PATH : /usr/share/gconf/gnome-classic.default.path
* DESKTOP_SESSION : gnome-classic
* DISPLAY : :0.0
* GDMSESSION : gnome-classic
* GNOME_DESKTOP_SESSION_ID : this-is-deprecated
* GNOME_KEYRING_CONTROL : /home/tfunck/.cache/keyring-cG5RcX
* GNOME_KEYRING_PID : 2422
* GPG_AGENT_INFO : /home/tfunck/.cache/keyring-cG5RcX/gpg:0:1
* HOME : /home/tfunck
* LANG : en_CA.UTF-8
* LANGUAGE : en_CA:en
* LD_LIBRARY_PATH : /data1/projects/mycode-quarantine/5.15/lib:/data1/projects/minc-quarantine/install/lib:
* LESSCLOSE : /usr/bin/lesspipe %s %s
* LESSOPEN : | /usr/bin/lesspipe %s
* LOGNAME : tfunck
* LS_COLORS : rs=0:di=01;34:ln=01;36:mh=00:pi=40;33:so=01;35:do=01;35:bd=40;33;01:cd=40;33;01:or=40;31;01:su=37;41:sg=30;43:ca=30;41:tw=30;42:ow=34;42:st=37;44:ex=01;32:*.tar=01;31:*.tgz=01;31:*.arj=01;31:*.taz=01;31:*.lzh=01;31:*.lzma=01;31:*.tlz=01;31:*.txz=01;31:*.zip=01;31:*.z=01;31:*.Z=01;31:*.dz=01;31:*.gz=01;31:*.lz=01;31:*.xz=01;31:*.bz2=01;31:*.bz=01;31:*.tbz=01;31:*.tbz2=01;31:*.tz=01;31:*.deb=01;31:*.rpm=01;31:*.jar=01;31:*.war=01;31:*.ear=01;31:*.sar=01;31:*.rar=01;31:*.ace=01;31:*.zoo=01;31:*.cpio=01;31:*.7z=01;31:*.rz=01;31:*.jpg=01;35:*.jpeg=01;35:*.gif=01;35:*.bmp=01;35:*.pbm=01;35:*.pgm=01;35:*.ppm=01;35:*.tga=01;35:*.xbm=01;35:*.xpm=01;35:*.tif=01;35:*.tiff=01;35:*.png=01;35:*.svg=01;35:*.svgz=01;35:*.mng=01;35:*.pcx=01;35:*.mov=01;35:*.mpg=01;35:*.mpeg=01;35:*.m2v=01;35:*.mkv=01;35:*.webm=01;35:*.ogm=01;35:*.mp4=01;35:*.m4v=01;35:*.mp4v=01;35:*.vob=01;35:*.qt=01;35:*.nuv=01;35:*.wmv=01;35:*.asf=01;35:*.rm=01;35:*.rmvb=01;35:*.flc=01;35:*.avi=01;35:*.fli=01;35:*.flv=01;35:*.gl=01;35:*.dl=01;35:*.xcf=01;35:*.xwd=01;35:*.yuv=01;35:*.cgm=01;35:*.emf=01;35:*.axv=01;35:*.anx=01;35:*.ogv=01;35:*.ogx=01;35:*.aac=00;36:*.au=00;36:*.flac=00;36:*.mid=00;36:*.midi=00;36:*.mka=00;36:*.mp3=00;36:*.mpc=00;36:*.ogg=00;36:*.ra=00;36:*.wav=00;36:*.axa=00;36:*.oga=00;36:*.spx=00;36:*.xspf=00;36:
* MANDATORY_PATH : /usr/share/gconf/gnome-classic.mandatory.path
* OLDPWD : /data1/projects/nipype/tf/tka_nipype/Tests/pipeline_flow/data
* ORBIT_SOCKETDIR : /tmp/orbit-tfunck
* PATH : /home/tfunck/.local/mendeleydesktop-1.13.6-linux-x86_64/bin/:/data1/projects/minc-quarantine/install/bin:/data1/projects/mycode-quarantine/5.15/bin:/home/tfunck/.local/mendeleydesktop-1.13.6-linux-x86_64/bin/:/data1/projects/mycode-quarantine/5.15/bin:/usr/lib/lightdm/lightdm:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games
* PWD : /data1/projects/nipype/tf/tka_nipype/Tests/pipeline_flow
* SESSION_MANAGER : local/ace-ws-30:@/tmp/.ICE-unix/2433,unix/ace-ws-30:/tmp/.ICE-unix/2433
* SHELL : /bin/bash
* SHLVL : 1
* SSH_AGENT_PID : 2468
* SSH_AUTH_SOCK : /home/tfunck/.cache/keyring-cG5RcX/ssh
* TERM : xterm
* TERMINATOR_UUID : urn:uuid:56b4499d-99cc-4a00-82dd-83f4df5cec02
* UBUNTU_MENUPROXY : libappmenu.so
* USER : tfunck
* WINDOWID : 50331652
* XAUTHORITY : /home/tfunck/.Xauthority
* XDG_CONFIG_DIRS : /etc/xdg/xdg-gnome-classic:/etc/xdg
* XDG_CURRENT_DESKTOP : GNOME
* XDG_DATA_DIRS : /usr/share/gnome-classic:/usr/share/gnome:/usr/local/share/:/usr/share/
* XDG_SEAT_PATH : /org/freedesktop/DisplayManager/Seat0
* XDG_SESSION_COOKIE : d1131ee17ae56c2491eab98500000001-1433171002.666296-390861529
* XDG_SESSION_PATH : /org/freedesktop/DisplayManager/Session0
* _ : /usr/bin/ipython

