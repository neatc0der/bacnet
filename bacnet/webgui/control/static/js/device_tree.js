(function ($) {
  function update_links() {
    $('a[rel="deviceTree"]').click(function (event) {
      pageurl = $(this).attr('href');

      $.deviceTree.reload(pageurl);

      if (pageurl != window.location) {
        window.history.pushState({path: pageurl}, '', pageurl);
      }

      return false;
    });

    function update_object(event, button, callback) {
      if (!button)
        button = $(this);
      var obj_id = $.deviceTree.currentObject;
      var device_id = $.deviceTree.currentDevice;
      var prop = button.attr('property');
      var old_content = button.html();
      var settings = $.deviceTree.settings;

      button.addClass('disabled');
      button.html('<img class="img-xs" src="' + settings.icon_url + 'ajax-loader.gif"/>');

      var transmission_data = {
        get: 'update',
        property: prop,
        object: obj_id,
        device: device_id
      };

      var current_obj = $.deviceTree.knownDevices[device_id];
      if (obj_id)
        current_obj = current_obj.objects_dict[obj_id];

      $.ajax({
        url: settings.ajax_url,
        method: 'POST',
        async: false,
        dataType: 'json',
        data: transmission_data,
        success: function (data, textStatus, jqXHR) {
          if (prop) {
            var my_intervall = setInterval(function () {
              var transmission_data = {
                get: 'update',
                property: prop,
                object: obj_id,
                device: device_id
              };
              $.ajax({
                url: settings.ajax_url,
                method: 'POST',
                async: true,
                dataType: 'json',
                data: transmission_data
              });

              transmission_data.get = 'property';

              $.ajax({
                url: settings.ajax_url,
                method: 'POST',
                async: false,
                dataType: 'json',
                data: transmission_data,
                success: function (data, textStatus, jqXHR) {
                  if (current_obj.short_id in data) {
                    var value = data[current_obj.short_id][prop].value;

                    if (data[current_obj.short_id][prop].updated < 5) {
                      clearInterval(my_intervall);
                      var index = $.deviceTree.updateIntervalls.indexOf(my_intervall);
                      delete $.deviceTree.updateIntervalls[index];

                      if (obj_id) {
                        if (!(prop in $.deviceTree.knownDevices[device_id].objects_dict[obj_id].properties_dict)) {
                          $.deviceTree.knownDevices[device_id].objects_dict[obj_id].properties_dict[prop] = {
                            name: prop
                          }
                        }
                        $.deviceTree.knownDevices[device_id].objects_dict[obj_id].properties_dict[prop].value = value;

                      } else {
                        $.deviceTree.knownDevices[device_id].properties_dict[prop].value = value;
                        if (prop == 'objectName') {
                          $.deviceTree.knownDevices[device_id].name = value;
                        }
                      }

                      button.parent().find('#value').html(get_value_content(current_obj, prop));

                      button.html(old_content);
                      button.removeClass('disabled');

                      if (callback)
                        callback();
                    }
                  }
                }
              });
            }, 1000);

            $.deviceTree.updateIntervalls[$.deviceTree.updateIntervalls.length] = my_intervall;

          } else {
            button.html(old_content);
            button.removeClass('disabled');

            if (callback)
              callback();
          }
        }
      }).fail(function () {
        button.html(button.html().replace('ajax-loader.gif', 'caution.svg'));
      });
    }

    $('a.deviceTreeRefresh').click(update_object);

    $('a.deviceTreeRefreshOnce').click(function (event) {
      var button = $(this);
      update_object(event, button, function () {
        button.addClass('disabled').addClass('btn-success');
      });
    });

    $('a.deviceTreeTransmit').click(function (event) {
      var button = $(this);
      var img = button.find('img');
      var old_icon = img.attr('src');
      var value = button.attr('value');
      var obj_id = $.deviceTree.currentObject;
      var device_id = $.deviceTree.currentDevice;
      var prop = button.attr('property');

      var settings = $.deviceTree.settings;

      button.addClass('disabled');
      img.attr('src', settings.icon_url + 'ajax-loader.gif');

      var transmission_data = {
        get: button.attr('command'),
        value: value,
        property: prop,
        device: device_id,
        object: obj_id
      };

      $.ajax({
        url: settings.ajax_url,
        method: 'POST',
        async: true,
        dataType: 'json',
        data: transmission_data,
        success: function (data, textStatus, jqXHR) {
          setTimeout(function () {
            update_object(event, button, function () {
              var value = '';
              if (obj_id)
                value = $.deviceTree.knownDevices[device_id].objects_dict[obj_id].properties_dict[prop].value;

              else
                value = $.deviceTree.knownDevices[device_id].properties_dict[prop].value;

              var img = button.find('img');

              if (value == 'active') {
                img.attr('src', old_icon.replace('binary-off', 'binary-on'));
                button.attr('value', 'inactive');

              } else if (value == 'inactive') {
                img.attr('src', old_icon.replace('binary-on', 'binary-off'));
                button.attr('value', 'active');

              } else {
                img.attr('src', old_icon);
              }
            });
          }, 500);
        }
      }).fail(function() {
        img.attr('src', settings.icon_url + 'caution.svg');
      });
    })
  }

  function update_devices() {
    $.ajax({
      url: $.deviceTree.settings.ajax_url,
      method: 'POST',
      async: false,
      dataType: 'json',
      data: {
        get: 'devices'
      },
      success: function (data, textStatus, jqXHR) {
        $.deviceTree.knownDevices = data;
      }
    });
  }

  function get_value_content(device, prop) {
    var value = '<span class="badge">?</span>';

    if (prop in device.properties_dict && device.properties_dict[prop].value) {
      prop = device.properties_dict[prop];
      value = prop.value;
      if (prop.name == 'presentValue' && (device.instance[0] == 'binaryOutput'
                                         || device.instance[0] == 'binaryValue'
                                         || device.instance[0] == 'binaryInput')) {
        var icon = $.deviceTree.settings.icon_url + 'binary-';
        var invert = 'active';
        if (value == 'active') {
          icon += 'on';
          invert = 'inactive';
        } else
          icon += 'off';
        value = '<img class="img-title" src="' + icon + '.svg"/>';

        var obj_data = 'property="' + prop.name + '" value="' + invert
                     + '" command ="write"';

        if ('binaryInput' != device.instance[0]) {
          value = '<a class="btn btn-default deviceTreeTransmit"' + obj_data
                + '>' + value + '</a>';
        }
      }

    } else if (prop in device.properties_dict) {
      value = '-';
    }

    return value;
  }

  $(window).bind('popstate', function() {
    $.deviceTree.reload(location.pathname)
  });

  $.deviceTree = function (settings) {
    $.deviceTree.settings = settings;

    $.deviceTree.updateIntervalls = [];

    $('#deviceTree').html(
      '<h1 id="deviceTreeTitle"></h1><br/><div id="deviceTreeContent"></div>'
    );

    update_devices();

    setInterval(update_devices, 60000);

    $.deviceTree.reload(window.location);
  };

  $.deviceTree.knownDevices = {};

  $.deviceTree.reload = function (pageurl) {
    var settings = $.deviceTree.settings;
    var left_menu = $('#left_menu');

    function update_menu() {
      var knownDevices = $.deviceTree.knownDevices;
      var active = 'active';
      if ($.deviceTree.currentDevice) {
        active = '';
      }

      left_menu.html(
        '<li class="' + active + '">'
        + '<a href="." rel="deviceTree">Überblick <span class="badge">'
        + Object.keys(knownDevices).length + '</span></a></li>'
      );

      for (var device in knownDevices) {
        if (device == $.deviceTree.currentDevice) {
          active = 'active';
        } else {
          active = '';
        }

        left_menu.append(
          '<li id="' + device + '" class="'
          + active + '"><a href="?device='
          + device + '" rel="deviceTree">'
          + knownDevices[device].name + '</a></li>'
        );
      }
    }

    function get_icon_img(obj) {
      var icon = '';
      var type = obj.instance[0];

      switch (type) {
        case 'device':
          if (obj.is_local_device)
            icon = 'computer';
          else
            icon = 'server';
          break;

        case 'file':
          icon = 'script';
          break;

        case 'program':
          icon = 'preferences';
          break;

        case 'analogValue':
        case 'analogInput':
        case 'analogOutput':
          icon = 'hardware';
          break;

        case 'binaryValue':
        case 'binaryInput':
        case 'binaryOutput':
          if (obj.presentValue == 'active')
            icon = 'binary-on';
          else
            icon = 'binary-off';
          break;

        default:
          icon = 'unknown';
      }

      return '<img class="img-title" src="' + settings.icon_url + icon + '.svg"/> ';
    }

    function get_objs_table(data, title, device) {
      var content = '';
      var keys = [];


      if ($.isArray(data)) {
        keys = data.sort();

      } else {
        var tmp = {};

        for (var key in data)
          tmp[data[key].name] = key;

        keys = Object.keys(tmp).sort();

        for (var key in keys)
          keys[key] = tmp[keys[key]];
      }

      for (var obj in keys) {
        obj = keys[obj];
        if (keys != data)
          obj = data[obj];

        if (isNaN(obj) && (obj[0] != 'device' || 'short_id' in obj)) {
          var obj_id = '';
          var href = '';

          if (!('instance' in obj)) {
            obj_id = obj[0] + '_' + obj[1];
            if (!$.isEmptyObject(device))
              href = '?device=' + device.short_id + '&object=' + obj_id;

          } else {
            obj_id = obj.short_id;
            href = '?device=' + obj_id;
          }

          if (!device || obj_id in device.objects_dict) {
            if (!$.isEmptyObject(device))
              obj = device.objects_dict[obj_id];

            content += '<tr><td>' + get_icon_img(obj) + ' <a href="' + href
                          + '" rel="deviceTree">' + obj.name;

            if (obj.is_device) {
              if (obj.is_local_device)
                content += ' (lokal)';

              else
                content += ' (' + obj.address_dict.address + ')';
            }

            content += '</a></td></tr>';

          } else {
            content += '<tr><td>' + obj + '</td></tr>';
          }
        }
      }
      content = '<h2>' + title + ' ('
                   + $('<table/>').html(content).find('tr').length
                   + ')</h2><div id="tubraunschweig_tabelle"><table><thead><tr>'
                   + '<th id="tabellenkopf_rot">Name</th></tr></thead><tbody>'
                   + content + '</table></div><br/>';

      return content
    }

    function render_content(device, parent_device) {
      var content = '';

      if ('objectList' in device.properties_dict && device.properties_dict.objectList.value[0] > 0) {
        content += get_objs_table(device.properties_dict.objectList.value, 'Objekte', device);
      } else if (device.is_device) {
        content += '<h2>keine Objekte</h2>';
      }

      if ('propertyList' in device.properties_dict && device.properties_dict.propertyList.value[0] > 0) {
        var this_content = '';
        for (var obj in device.properties_dict.propertyList.value.sort()) {
          obj = device.properties_dict.propertyList.value[obj];
          var prop_name = obj;
          if (isNaN(obj) && obj != 'propertyList' && obj != 'objectList') {
            this_content += '<tr><td>' + obj + '</td><td>';
            var value = get_value_content(device, obj);

            if (!$('<div/>').html(value).find('a').length)
              value = '<div id="value">' + value + '</div> <a class="btn btn-default btn-xs '
                    + 'pull-right deviceTreeRefresh" property="'
                    + prop_name + '"><span class="glyphicon glyphicon-refresh"></span></a>';

            this_content += value + '</td></tr>';
          }
        }

        if (device.instance[0] == 'file' && device.file_content) {
          var replace_linebreak = new RegExp('\n', 'g');
          var replace_space = new RegExp(' ', 'g');
          this_content += '<tr><td>Datei</td><td><code style="font-size: 0.75em;">'
                          + device.file_content.replace(replace_linebreak, '<br>')
                                  .replace(replace_space, '&nbsp;') + '</code></td></tr>';
        }

        if (!$('<table/>').html(this_content).find('tr').length) {
          content += '<h2> keine Eigenschaften</h2>'
        } else {
          content += '<h2>Eigenschaften ('
                     + $('<table/>').html(this_content).find('tr').length
                     + ')</h2><div id="tubraunschweig_tabelle"><table><thead><tr>'
                     + '<th id="tabellenkopf_rot">Name</th><th id="tabellenkopf_rot">Wert'
                     + '</th></tr></thead><tbody>'
                     + this_content + '</tbody></table></div><br/>';
        }
      } else {
        content += '<h2>keine Eigenschaften</h2>';
      }



      return content;
    }

    function update_content() {
      var device = {};
      var obj = {};
      var use_obj = {};

      if ($.deviceTree.currentDevice in $.deviceTree.knownDevices) {
        device = $.deviceTree.knownDevices[$.deviceTree.currentDevice];
        use_obj = device;
        if ($.deviceTree.currentObject in device.objects_dict) {
          obj = device.objects_dict[$.deviceTree.currentObject];
          use_obj = obj;
        }
        device.content = render_content(use_obj, device);

      } else {
        device = {
          name: 'Geräteübersicht',
          content: get_objs_table($.deviceTree.knownDevices, 'Geräte')
        }
      }

      var title = device.name;
      if ('address_dict' in device) {
        if (device.is_local_device)
          title += ' (lokal)';

        else
          title += ' (' + device.address_dict.address + ')';
      }

      var content = device.content;
      if ('name' in obj) {
        title += ' - ' + obj.name;
        content = '<p><a href="?device=' + device.short_id + '" rel="deviceTree">'
                + '<span class="glyphicon glyphicon-chevron-left"></span>'
                + device.name + '</a></p><br/>' + content;
      }

      if ('instance' in use_obj) {
        var icon = get_icon_img(use_obj);

        title = icon + title + '<a class="btn btn-default btn-medium pull-right '
              + 'deviceTreeRefreshOnce">' + '<span class="glyphicon glyphicon-refresh"></span></a>';
      }

      $('#deviceTreeTitle').html(title);
      $('#deviceTreeContent').html(content);
    }

    $.deviceTree.currentDevice = $.getQuery('device', pageurl);
    $.deviceTree.currentObject = $.getQuery('object', pageurl);
    $.deviceTree.currentProperty = $.getQuery('property', pageurl);

    update_menu();
    update_content();

    update_links();
  };
})(jQuery);
