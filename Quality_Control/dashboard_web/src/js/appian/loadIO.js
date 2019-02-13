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

    req.open('GET', 'nodes.xml');
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
        dataCSV=readCSV(this.responseText);
        // console.log(dataCSV);
        getResults(dataCSV, stage, level, type);
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

    var menuSt=document.createElement("li");
    menuSt.innerHTML="<a href=\"javascript:;\" >Stats</a>";
    var subStats=document.createElement("ul");
    subStats.className="collapse";


    lvlvar = ['sub', 'ses', 'task'];
    levels = ['Subjects', 'Session', 'Task'];
    l=0;

    lvlvar.forEach(function(level) {
    subStLevel=document.createElement("ul");
    subStLevel.className="collapse";
    StLevel=document.createElement("li");
    StLevel.innerHTML="<a href=\"javascript:;\" onclick=\"reachCSV(\'"+stage+"\',\'"+level+"\',\'stats\')\">"+levels[l++]+"</a>";
    StLevel.appendChild(subStLevel);
    subStats.appendChild(StLevel);
    menuSt.appendChild(subStats);
    });

    menuSt.appendChild(subStats);

    var menuQC=document.createElement("li");
    menuQC.innerHTML="<a href=\"javascript:;\" onclick=\"reachCSV(\'"+stage+"\',\'none\',\'qc\')\">QC</a>";
    var subStats=document.createElement("ul");
    subStats.className="collapse";

    menuQC.appendChild(subStats);

    for(var s=0;s<tabScans.length;s++){
        var subScanI=document.createElement("li");
        arr = tabScans[s].attributes
        Object.keys(arr).forEach(element => {
          switch(arr[element].name){
            case "sid":
                sid=arr[element].value;
                break;
            case "ses":
                ses=arr[element].value;
                break;
            case "task":
                task=arr[element].value;
                break;
            }
        });
       	id="sub-"+sid+"_"+"ses-"+ses+"_"+"task-"+task

        subScanI.innerHTML="<a href=\"javascript:;\" onclick=\"deployPage(tabScans,"+s+",\'"+id+"\',\'"+stageXml+"\')\">"+id+"</a>";
        $node.append(subScanI);
        document.getElementById(stage).append(subScanI);

    }
    document.getElementById(stage).append(menuSt);
    document.getElementById(stage).append(menuQC);
    });

}







var readCSV = function (allText) {
    var allTextLines = allText.split(/\r\n|\n/);
    var headers = allTextLines[0].split(',');
    var dataCSV = [];i=1;
    while (i!=allTextLines.length-1) {
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
	i++;
	}

    if(dataCSV !== null && dataCSV !== "" && dataCSV.length > 1) {
      // getResults(dataCSV, stage, level); 
      return dataCSV; 
    }


};





var getResults = function(dataCSV, stage, level, type) {

    rowLength = dataCSV.length;
    // Combine all data into single arrays

    stageList = dataCSV.map(function(elem){return elem.analysis;});
    if(stage === 'pet-coregistration'){
        indices = stageList.map((e, i) => e === stage || e === 'initialization' ? i : '').filter(String);
    }else if(stage === 'tka'){
        indices = stageList.map((e, i) => e === stage || e === 'quantification' ? i : '').filter(String);
    }else{
        indices = stageList.map((e, i) => e === stage ? i : '').filter(String);
    }

    metricList = dataCSV.map(function(elem){return elem.metric;});
    subjList = dataCSV.map(function(elem){return elem.sub;});
    valueList = dataCSV.map(function(elem){return elem.value;});
    roiList = dataCSV.map(function(elem){return elem.roi;});

    valueStage=[];roiStage=[];subjStage=[];
    valueList.forEach(function (value, i) {
        if (indices.includes(i)){
            valueStage.push(value);
            roiStage.push(metricList[i]);
            // roiStage.push(roiList[i]);
            subjStage.push(subjList[i]);
    }});

    xaxis_title = "ROI";
    yaxis_title = "";

    switch (stage) {
        case 'pet-coregistration':
        case 'coreg':
            title_plot = "COREGISTRATION";
            break;
        case 'pvc':
            title_plot = "PARTIAL VOLUME CORRECTION";
            break;
        case 'tka':
            title_plot = "TRACER KINETIC ANALYSIS";
            break;
    }
    if (type == 'qc'){
    	titleDiv = "Quantitative QC";
    }else{
    	titleDiv = "Statistics ("+level+")";

    }

    displayPlotBrowser(level,roiStage,valueStage,subjStage,
        xaxis_title,yaxis_title,title_plot,titleDiv);

};







