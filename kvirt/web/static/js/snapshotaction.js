function snapshotcreate(name){
  var snapshot = prompt("Enter snapshot name");
  if (snapshot == null) {
     return ;
  }
  $("#wheel").show();
  data = {'snapshot': snapshot};
  $.ajax({
       type: "POST",
        url: `/snapshots/${name}`,
        data: data,
        success: function(data) {
            $("#wheel").hide();
            if (data.result == 'success') {
                $('.top-right').notify({message: { text: "Snapshot "+snapshot+" created!!!" }, type: 'success'}).show();
            } else {
                $('.top-right').notify({message: { text: "Snapshot "+snapshot+" not created because "+data.reason }, type: 'danger'}).show();
            };
        }
    });
}

function snapshotdelete(name){
  $.ajax({
       type: "GET",
        url: `/snapshots/${name}`,
        success: function(snapshots) {
            if (snapshots.length == 0) {
                $('.top-right').notify({message: { text: "No snapshots found for "+name }, type: 'danger'}).show();
                return
            } else {
                var snapshot = prompt("Choose snapshots between the following ones:\n"+snapshots);
                if (snapshot == null) {
                   return ;
                }
                $("#wheel").show();
                data = {'snapshot': snapshot};
                $.ajax({
                     type: "DELETE",
                      url: `/snapshots/${name}`,
                      data: data,
                      success: function(data) {
                          $("#wheel").hide();
                          if (data.result == 'success') {
                              $('.top-right').notify({message: { text: "Snapshot "+snapshot+" deleted!!!" }, type: 'success'}).show();
                          } else {
                              $('.top-right').notify({message: { text: "Snapshot "+snapshot+" not deleted because "+data.reason }, type: 'danger'}).show();
                          };
                      }
                  });
                          };
                      }
                  });
}

function snapshotrevert(name){
  $.ajax({
       type: "GET",
        url: `/snapshots/${name}`,
        success: function(snapshots) {
            if (snapshots.length == 0) {
                $('.top-right').notify({message: { text: "No snapshots found for "+name }, type: 'danger'}).show();
                return
            } else {
                var snapshot = prompt("Choose snapshots between the following ones:\n"+snapshots);
                if (snapshot == null) {
                   return ;
                }
                $("#wheel").show();
                data = {'snapshot': snapshot};
                $.ajax({
                     type: "POST",
                      url: `/snapshots/${name}/revert`,
                      data: data,
                      success: function(data) {
                          $("#wheel").hide();
                          if (data.result == 'success') {
                              $('.top-right').notify({message: { text: "Snapshot "+snapshot+" Reverted!!!" }, type: 'success'}).show();
                          } else {
                              $('.top-right').notify({message: { text: "Snapshot "+snapshot+" Not reverted because "+data.reason }, type: 'danger'}).show();
                          };
                      }
                  });
                          };
                      }
                  });
}
