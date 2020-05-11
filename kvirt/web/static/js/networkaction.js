function networkcreate(){
  $("#wheel").show();
  var network = $("#network").val();
  var cidr = $("#cidr").val();
  var isolated = $("#isolated").val();
  var dhcp = $("#dhcp").val();
  data = {'network': network, 'cidr': cidr, 'dhcp': dhcp, 'isolated': isolated, 'action': 'create'};
  $.ajax({
       type: "POST",
        url: '/networkaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Network "+network+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Network "+network+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function networkdelete(network){
  $("#wheel").show();
  data = {'network': network, 'action': 'delete'};
  $.ajax({
       type: "POST",
        url: '/networkaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Network "+network+" Deleted!!!" }, type: 'success'}).show();
                networkstable();
            } else {
                $('.top-right').notify({message: { text: "Network "+network+" not deleted :because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
