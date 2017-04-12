function vmstart(vm){
  $("#wheel").show();
  data = {'name': vm, 'action': 'start'};
  $.ajax({  
       type: "POST",
        url: '/vmaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Vm "+vm+" Started!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" Failed to Start" }, type: 'danger'}).show(); 
            };
		}
	});
}

function vmstop(vm){
  $("#wheel").show();
  data = {'name': vm, 'action': 'stop'};
  $.ajax({  
       type: "POST",
        url: '/vmaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Vm "+vm+" Stopped!!!" }, type: 'success'}).show(); 
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" Failed to Stop" }, type: 'danger'}).show(); 
            };
		}
	});
}

function vmdelete(vm){
  $("#wheel").show();
  data = {'name': vm, 'action': 'delete'};
  var r = confirm("Are you sure you want to delete this VM?");
  if (r != true) {
    return ;
  }
  $.ajax({
       type: "POST",
        url: '/vmaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data == '0') {
                $('.top-right').notify({message: { text: "Vm "+vm+" Deleted!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" Failed to Delete" }, type: 'danger'}).show();
            };
        }
    });
}

function vmcreate(name, profile){
  if (name == '') {
    var name = prompt("Enter vm name");
    if (name == null) {
        return ;
    }
  }
  $("#wheel").show();
  data = {'name': name, 'action': 'create', 'profile': profile};
  $.ajax({
       type: "POST",
        url: '/vmaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data == '0') {
                $('.top-right').notify({message: { text: "Vm "+name+" Created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "VM "+name+" Failed to Create" }, type: 'danger'}).show();
            };
        }
    });
}
