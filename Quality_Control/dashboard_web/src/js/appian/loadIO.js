function collectIO(){
    var req = null;
    if (XMLHttpRequest) {
        req = new XMLHttpRequest();
    } else {
        req = new ActiveXObject("Microsoft.XMLHTTP");
    }

    req.onreadystatechange = function(event) {
    if (this.readyState === XMLHttpRequest.DONE) {
    if (this.status === 200) {
        menuQC(this.responseXML);
    } else {
        console.log("Response statut: %d (%s)", this.status, this.statusText);
    }}};

    req.open('GET', 'nodes_2.xml');
    req.send(null);
}




function reachCSV(stage, level, type){
    var req = null;
    if (XMLHttpRequest) {
        req = new XMLHttpRequest();
    } else {
        req = new ActiveXObject("Microsoft.XMLHTTP");}
    req.onreadystatechange = function(event) {
    if (this.readyState === XMLHttpRequest.DONE) {
    if (this.status === 200) {
        readCSV(this.responseText, stage, level);
    } else {
        console.log("Status de la réponse: %d (%s)", this.status, this.statusText);
    }}};

    switch(type){
        case 'stats': 
            req.open('GET', "stats/"+level+"/descriptive_statistics_"+level+".csv");
            break;
        case 'qc': 
            stage = stage === 'pet-coregistration' ? 'coreg' : stage;
            req.open('GET', "qc/"+stage+"/metrics/"+stage+"_qc_metrics.csv");
            break;
    };
    req.send(null);
}





function menuQC(xmlNodes){

    tabScans=xmlNodes.getElementsByTagName("scan");

    array = ['pet-coregistration', 'pvc', 'tka'];

    array.forEach(function(stage) {

    var subScanS=document.createElement("li");
    subScanS.innerHTML="<a href=\"javascript:;\" >Stats</a>";
    var subScanC=document.createElement("ul");
    subScanC.className="collapse";


    levels = ['sub', 'ses', 'task'];
    levelsMenu = ['Subjects', 'Session', 'Task'];
    l=0;

    levels.forEach(function(level) {
    subScanSubC=document.createElement("ul");
    subScanSubC.className="collapse";
    subScanSub=document.createElement("li");
    subScanSub.innerHTML="<a href=\"javascript:;\" onclick=\"reachCSV(\'"+stage+"\',\'"+level+"\',\'stats\')\">"+levelsMenu[l++]+"</a>";
    subScanSub.appendChild(subScanSubC);
    subScanC.appendChild(subScanSub);
    subScanS.appendChild(subScanC);
    });

    subScanS.appendChild(subScanC);

    var subScanQ=document.createElement("li");
    subScanQ.innerHTML="<a href=\"javascript:;\" onclick=\"reachCSV(\'"+stage+"\',\'none\',\'qc\')\">QC</a>";
    var subScanC=document.createElement("ul");
    subScanC.className="collapse";

    subScanQ.appendChild(subScanC);

    tabScans=xmlNodes.getElementsByTagName("scan");
    for(var s=0;s<tabScans.length;s++){
        var subScanI=document.createElement("li");
        arr = tabScans[s].attributes
        Object.keys(arr).forEach(element => {
          switch(arr[element].name){
            case "sid":
                sid=arr[element].value;
            case "ses":
                ses=arr[element].value;
            case "task":
                task=arr[element].value;
            }
        });
       

        switch(stage){
            case "pet-coregistration":
                stageXml='pet2mri';
                $node = $("#coreg");
                break;
            case "pvc":
                stageXml='pvc';
                $node = $("#pvc");
                break;
            case "tka":
                stageXml='tka';
                $node = $("#tka");
                break;
        }

        subScanI.innerHTML="<a href=\"javascript:;\" onclick=\"deployPage(tabScans,"+s+",\'"+stageXml+"\')\">"+"sub-"+sid+"_"+"ses-"+ses+"_"+"task-"+task+"</a>";
        $node.append(subScanI);
        document.getElementById(stage).append(subScanI);

    }
    document.getElementById(stage).append(subScanS);
    document.getElementById(stage).append(subScanQ);

    });

}







var readCSV = function (allText, stage, level) {
    var allTextLines = allText.split(/\r\n|\n/);
    var headers = allTextLines[0].split(',');
    var dataCSV = [];
    for (var i=1; i<allTextLines.length; i++) {
        var line = allTextLines[i].split(',');
        if (line.length == headers.length) {
            var tarr = {};
                for (var j=0; j<headers.length; j++) {
                    keyCol=headers[j];
                    valueCol=line[j];
                    tarr[keyCol]=valueCol;
                }
                dataCSV.push(tarr);
        }
    }

    if(dataCSV !== null && dataCSV !== "" && dataCSV.length > 1) {          
      getResults(dataCSV, stage, level); 
    }           
};





var getResults = function(dataCSV, stage, level) {

    subjList = dataCSV.map(function(elem){return elem.sub;});
    rowLength = dataCSV.length;
    // Combine all data into single arrays

    stageList = dataCSV.map(function(elem){return elem.analysis;});
    if(stage === 'pet-coregistration'){
        indices = stageList.map((e, i) => e === 'pet-coregistration' || e === 'prelimaries' ? i : '').filter(String);
    }else{
        indices = stageList.map((e, i) => e === stage ? i : '').filter(String);
    }

    metric = dataCSV.map(function(elem){return elem.metric;});
    subjList = dataCSV.map(function(elem){return elem.sub;});
    valueList = dataCSV.map(function(elem){return elem.value;});
    roiList = dataCSV.map(function(elem){return elem.roi;});

    valueStage=[];roiStage=[];subjStage=[];
    valueList.forEach(function (value, i) {
        if (indices.includes(i)){
            valueStage.push(value);
            roiStage.push(roiList[i]);
            subjStage.push(subjList[i]);
    }});

    xaxis_title = "ROI";
    yaxis_title = ("TAC %s", metric[0]);

    switch (stage) {
        case 'pet-coregistration':
            title = "COREGISTRATION";
            break;
        case 'pvc':
            title = "PARTIAL VOLUME CORRECTION";
            break;
        case 'tka':
            title = "TRACER KINETIC ANALYSIS";
            break;
    }

    displayPlotBrowser(level,roiStage,valueStage,subjStage,
        xaxis_title,yaxis_title,title);

};







