function vmstart(name){
  $("#wheel").show();
  $.ajax({  
       type: "POST",
        url: `/vms/${name}/start`,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Vm "+name+" started!!!" }, type: 'success'}).show(); 
                vmstable();
            } else {
                $('.top-right').notify({message: { text: "VM "+name+" not started" }, type: 'danger'}).show(); 
            };
		}
	});
}

function vmstop(name){
  $("#wheel").show();
  $.ajax({  
       type: "POST",
        url: `/vms/${name}/stop`,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Vm "+name+" stopped!!!" }, type: 'success'}).show(); 
                vmstable();
            } else {
                $('.top-right').notify({message: { text: "VM "+name+" not stopped" }, type: 'danger'}).show(); 
            };
		}
	});
}

function vmdelete(name){
  $("#wheel").show();
  var r = confirm("Are you sure you want to delete this VM?");
  if (r != true) {
    return ;
  }
  $.ajax({
       type: "DELETE",
        url: `/vms/${name}`,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Vm "+name+" deleted!!!" }, type: 'success'}).show();
                vmstable();
            } else {
                $('.top-right').notify({message: { text: "VM "+name+" not deleted because "+data.reason }, type: 'danger'}).show();
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
  data = {'name': name, 'profile': profile, 'parameters': parameters};
  $.ajax({
       type: "POST",
        url: '/vms',
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
