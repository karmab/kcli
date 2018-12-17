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
                $('.top-right').notify({message: { text: "Vm "+vm+" started!!!" }, type: 'success'}).show(); 
                vmstable();
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" not started" }, type: 'danger'}).show(); 
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
                $('.top-right').notify({message: { text: "Vm "+vm+" stopped!!!" }, type: 'success'}).show(); 
                vmstable();
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" not stopped" }, type: 'danger'}).show(); 
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
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Vm "+vm+" deleted!!!" }, type: 'success'}).show();
                vmstable();
            } else {
                $('.top-right').notify({message: { text: "VM "+vm+" not deleted because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function vmcreate(name, profile){
 if (name === undefined) {
  name = $("#name").val();
 }
 else if (name == '') {
    var name = prompt("Enter vm name or leave blank to autogenerate one");
    if (name === null) {
    return;
    }
 }
 if (profile === undefined) {
  profile = $("#profile").val();
 }
 var parameters = {};
 $.each($('#createvmform').serializeArray(), function() {
    parameters[this.name] = this.value;
 });
  $("#wheel").show();
  data = {'name': name, 'action': 'create', 'profile': profile, 'parameters': parameters};
  $.ajax({
       type: "POST",
        url: '/vmaction',
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                if ( name == '' ) {
                name = data.vm
                }
                $('.top-right').notify({message: { text: "Vm "+name+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "VM "+name+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}
