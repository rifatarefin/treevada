function validityChecker(sys)
% Have to use namespace to call functions in packagaes. POOR DESIGN BY
% MATHWORKS: https://www.mathworks.com/matlabcentral/answers/399880-call-function-in-package-from-package
    % sys is the path to the directory of mdl files
    [list_of_files] = dir(sys);
    dst_sys = strrep(sys,filesep,''); 
    tf = ismember( {list_of_files.name}, {'.', '..'});
    list_of_files(tf) = [];  %remove current and parent directory.
    
    all_experiment_dir = 'Experiments';
    working_dir= [all_experiment_dir filesep 'ValidityCheckerRes']
    if ~exist(working_dir, 'dir')
        mkdir(working_dir);
    end
    [processed_files] = vertcat(dir([working_dir filesep dst_sys filesep 'Compiled']),dir([working_dir filesep dst_sys filesep 'NotCompiled']),dir([working_dir filesep dst_sys filesep 'LoadError']));
    processed_names = {};
    for i = 1: numel(processed_files)
        processed_names{end+1} = processed_files(i).name;
    end

    processed_file_count = 1;
    %Loop over each Zip File 
    error_models = 0 ;
    err = [""];
        lst = [" "];
    for cnt = 1 : size(list_of_files) 

        name = strtrim(char(list_of_files(cnt).name)) ;
        if sum(ismember(processed_names, name))
            continue
        end
        model_name = strrep(name,'.slx','');
        model_name = strrep(model_name,'.mdl','');

 

        disp(['Before loading  : ' num2str(cnt) ' ' model_name]);
        try
            load_system([sys filesep name])
        catch ME
            err(end+1) = model_name;
            if ~exist([working_dir filesep dst_sys filesep 'LoadError'], 'dir')
                mkdir([working_dir filesep dst_sys filesep 'LoadError']);
            end
            copyfile([sys filesep name],[working_dir filesep dst_sys filesep 'LoadError'])

            continue
        end
        disp(['Processing  : ' num2str(cnt) ' ' model_name]);



    %{%}
    try
        %load_system([sys filesep name]);
       disp(['before Simulates  : ' model_name]);
       simulates = validityChecker.does_model_simulate(model_name);
        
       disp(['after Simulates  : ' model_name]);
       if simulates == 1
            disp(['Simulates  : ' model_name]);
            if ~exist([working_dir filesep dst_sys filesep 'Simulates'], 'dir')
                mkdir([working_dir filesep dst_sys filesep 'Simulates'])
            end
            copyfile([sys filesep name],[working_dir filesep dst_sys filesep 'Simulates'])

        end
    catch ME
        disp(['catch Simulates  : ' model_name]);
        %fprintf('ERROR Compiling %s\n');                    
        %disp(['ERROR ID : ' ME.identifier]);
       %disp(['ERROR MSG : ' ME.message]);
        bdclose("all");

    end
    %{%}
        bdclose("all");
    end
end
