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
