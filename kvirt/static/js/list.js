function vmstable() {
    $.ajax({
         type: "GET",
          url: '/vmstable',
          success: function(data) {
            $('#vms').html(data);
            $('#vms').dataTable({
            "order": [[ 1, "asc" ]],
            stateSave: true,
            retrieve: true,
            });
          }
    });
    $('[data-toggle="tooltip"]').tooltip();
}

function vmprofilestable() {
    $.ajax({
         type: "GET",
          url: '/vmprofilestable',
          success: function(data) {
            $('#profiles').html(data);
            $('#profiles').dataTable({
            retrieve: true,
            });
          }
    });
}

function imagestable() {
    $.ajax({
         type: "GET",
          url: '/imagestable',
          success: function(data) {
            $('#images').html(data);
            $('#images').dataTable({
            retrieve: true,
            });
          }
    });
}

function repostable() {
    $.ajax({
         type: "GET",
          url: '/repostable',
          success: function(data) {
            $('#repos').html(data);
            $('#repos').dataTable({
            retrieve: true,
            });
          }
    });
}

function productstable() {
    $.ajax({
         type: "GET",
          url: '/productstable',
          success: function(data) {
            $('#products').html(data);
            $('#products').dataTable({
            retrieve: true,
            });
          }
    });
}

function planstable() {
    $.ajax({
         type: "GET",
          url: '/planstable',
          success: function(data) {
            $('#plans').html(data);
            $('#plans').dataTable({
            retrieve: true,
            });
          }
    });
}

function kubestable() {
    $.ajax({
         type: "GET",
          url: '/kubestable',
          success: function(data) {
            $('#kubes').html(data);
            $('#kubes').dataTable({
            retrieve: true,
            });
          }
    });
}

function isostable() {
    $.ajax({
         type: "GET",
          url: '/isostable',
          success: function(data) {
            $('#isos').html(data);
            $('#isos').dataTable({
            retrieve: true,
            });
          }
    });
}

function networkstable() {
    $.ajax({
         type: "GET",
          url: '/networkstable',
          success: function(data) {
            $('#networks').html(data);
            $('#networks').dataTable({
            retrieve: true,
            });
          }
    });
}

function containerstable() {
    $.ajax({
         type: "GET",
          url: '/containerstable',
          success: function(data) {
            $('#containers').html(data);
            $('#containers').dataTable({
            retrieve: true,
            });
          }
    });
}

function containerprofilestable() {
    $.ajax({
         type: "GET",
          url: '/containerprofilestable',
          success: function(data) {
            $('#profiles').html(data);
            $('#profiles').dataTable({
            retrieve: true,
            });
          }
    });
}

function poolstable() {
    $.ajax({
         type: "GET",
          url: '/poolstable',
          success: function(data) {
            $('#pools').html(data);
            $('#pools').dataTable({
            retrieve: true,
            });
          }
    });
}

function hoststable() {
    $.ajax({
         type: "GET",
          url: '/hoststable',
          success: function(data) {
            $('#hosts').html(data);
            $('#hosts').dataTable({
            retrieve: true,
            });
          }
    });
}
